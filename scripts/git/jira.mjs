#!/usr/bin/env node
/**
 * Jira 통합 스크립트 – 코멘트 추가/삭제, post-commit, 작업 요약, 코멘트 파일 생성
 *
 * 사용법:
 *   node scripts/git/jira.mjs post-commit              # 커밋 후 이슈에 코멘트 자동 추가
 *   node scripts/git/jira.mjs comment "내용" [--issue WEB-123]
 *   node scripts/git/jira.mjs comment @파일.txt [--issue WEB-123]
 *   node scripts/git/jira.mjs log "사용자요청" "AI응답" [--issue WEB-123]
 *   node scripts/git/jira.mjs summary "요약" [--issue WEB-123]
 *   node scripts/git/jira.mjs summary --file 파일.txt [--issue WEB-123]
 *   node scripts/git/jira.mjs delete [--issue WEB-123]
 *   node scripts/git/jira.mjs create-comment-file      # jira-comment.txt 템플릿 생성
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const ROOT = process.cwd();
const DEFAULT_ISSUE = process.env.DEFAULT_ISSUE_KEY || process.env.JIRA_PROJECT_KEY || 'WEB-295';

function loadEnv() {
  for (const file of ['.env.local', '.env']) {
    try {
      const env = readFileSync(join(ROOT, file), 'utf-8');
      for (const line of env.split('\n')) {
        const [key, ...vals] = line.split('=');
        if (key && vals.length) {
          const val = vals.join('=').trim().replace(/^["']|["']$/g, '');
          if (!process.env[key.trim()]) process.env[key.trim()] = val;
        }
      }
    } catch (_) {}
  }
}
loadEnv();

const JIRA_URL = process.env.JIRA_URL?.replace(/\/$/, '');
const JIRA_EMAIL = process.env.JIRA_EMAIL;
const JIRA_API_TOKEN = process.env.JIRA_API_TOKEN;

function getAuth() {
  if (!JIRA_URL || !JIRA_EMAIL || !JIRA_API_TOKEN) {
    throw new Error('JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN 환경 변수를 설정하세요.');
  }
  return Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64');
}

function parseArgs() {
  const args = process.argv.slice(2);
  const cmd = args[0];
  const opts = {};
  const rest = [];
  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--issue' || args[i] === '-i') {
      opts.issue = args[++i];
    } else if (args[i] === '--file' || args[i] === '-f') {
      opts.file = args[++i];
    } else if (!args[i].startsWith('--')) {
      rest.push(args[i]);
    }
  }
  return { cmd, opts, rest };
}

function readContent(arg) {
  if (!arg) return '';
  if (arg.startsWith('@')) {
    const p = join(ROOT, arg.slice(1));
    const raw = readFileSync(p, 'utf-8');
    return raw.replace(/^\uFEFF/, '').trim();
  }
  return arg.trim();
}

function ensureUtf8(text) {
  if (typeof text !== 'string') return text;
  try {
    Buffer.from(text, 'utf-8').toString('utf-8');
    return text;
  } catch (_) {
    return Buffer.from(text, 'latin1').toString('utf-8');
  }
}

function textToJiraBody(text) {
  const lines = ensureUtf8(text).split('\n').filter((l) => l.trim());
  const content = [];
  for (const line of lines) {
    if (line.match(/^\*\*.*\*\*:$/)) {
      content.push({
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: line.replace(/\*\*/g, '') }],
      });
    } else if (line.match(/\*\*.*\*\*/)) {
      const parts = [];
      let rest = line;
      let m;
      while ((m = rest.match(/\*\*(.*?)\*\*/)) !== null) {
        if (m.index > 0) parts.push({ type: 'text', text: rest.slice(0, m.index) });
        parts.push({ type: 'text', marks: [{ type: 'strong' }], text: m[1] });
        rest = rest.slice(m.index + m[0].length);
      }
      if (rest) parts.push({ type: 'text', text: rest });
      content.push({
        type: 'paragraph',
        content: parts.length ? parts : [{ type: 'text', text: line }],
      });
    } else {
      content.push({
        type: 'paragraph',
        content: [{ type: 'text', text: line }],
      });
    }
  }
  return {
    body: {
      type: 'doc',
      version: 1,
      content: content.length ? content : [{ type: 'paragraph', content: [{ type: 'text', text: '' }] }],
    },
  };
}

function markdownToJiraDoc(text) {
  text = text.replace(/^\uFEFF/, '');
  const lines = text.split('\n');
  const content = [];
  let listItems = [];
  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      if (listItems.length) {
        content.push({ type: 'bulletList', content: listItems });
        listItems = [];
      }
      content.push({ type: 'paragraph', content: [{ type: 'text', text: '' }] });
      continue;
    }
    if (t.startsWith('### ')) {
      if (listItems.length) {
        content.push({ type: 'bulletList', content: listItems });
        listItems = [];
      }
      content.push({
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: t.slice(4) }],
      });
    } else if (t.startsWith('## ')) {
      if (listItems.length) {
        content.push({ type: 'bulletList', content: listItems });
        listItems = [];
      }
      content.push({
        type: 'heading',
        attrs: { level: 2 },
        content: [{ type: 'text', text: t.slice(3) }],
      });
    } else if (t.startsWith('# ')) {
      if (listItems.length) {
        content.push({ type: 'bulletList', content: listItems });
        listItems = [];
      }
      content.push({
        type: 'heading',
        attrs: { level: 1 },
        content: [{ type: 'text', text: t.slice(2) }],
      });
    } else if (t.startsWith('- ')) {
      listItems.push({
        type: 'listItem',
        content: [{ type: 'paragraph', content: [{ type: 'text', text: t.slice(2) }] }],
      });
    } else {
      if (listItems.length) {
        content.push({ type: 'bulletList', content: listItems });
        listItems = [];
      }
      content.push({
        type: 'paragraph',
        content: [{ type: 'text', text: t }],
      });
    }
  }
  if (listItems.length) content.push({ type: 'bulletList', content: listItems });
  return {
    type: 'doc',
    version: 1,
    content: content.length ? content : [{ type: 'paragraph', content: [{ type: 'text', text: text }] }],
  };
}

async function jiraFetch(pathname, method = 'GET', body = null) {
  const auth = getAuth();
  const url = `${JIRA_URL}/rest/api/3/issue/${pathname}`;
  const opts = {
    method,
    headers: {
      Authorization: `Basic ${auth}`,
      Accept: 'application/json',
      'Content-Type': 'application/json; charset=utf-8',
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.errorMessages?.join(', ') || data.message || res.statusText);
  return data;
}

async function addComment(issueKey, bodyPayload) {
  const res = await fetch(`${JIRA_URL}/rest/api/3/issue/${issueKey}/comment`, {
    method: 'POST',
    headers: {
      Authorization: `Basic ${getAuth()}`,
      Accept: 'application/json',
      'Content-Type': 'application/json; charset=utf-8',
    },
    body: JSON.stringify(bodyPayload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.errorMessages?.join(', ') || res.statusText);
  return data;
}

async function postCommit() {
  let hash, message, author, date, files, stats;
  try {
    hash = execSync('git rev-parse HEAD', { encoding: 'utf-8', cwd: ROOT }).trim();
    message = execSync('git log -1 --pretty=%B', { encoding: 'utf-8', cwd: ROOT }).trim();
    author = execSync('git log -1 --pretty=%an', { encoding: 'utf-8', cwd: ROOT }).trim();
    date = execSync('git log -1 --pretty=%ai', { encoding: 'utf-8', cwd: ROOT }).trim();
    files = execSync('git diff-tree --no-commit-id --name-only -r HEAD', { encoding: 'utf-8', cwd: ROOT })
      .trim()
      .split('\n')
      .filter(Boolean);
    const numstat = execSync('git diff-tree --no-commit-id --numstat -r HEAD', { encoding: 'utf-8', cwd: ROOT })
      .trim()
      .split('\n')
      .filter(Boolean)
      .map((line) => line.split('\t'));
    stats = numstat.reduce(
      (acc, [add, del]) => ({
        additions: acc.additions + (parseInt(add, 10) || 0),
        deletions: acc.deletions + (parseInt(del, 10) || 0),
      }),
      { additions: 0, deletions: 0 }
    );
  } catch (e) {
    console.warn('⚠️ 커밋 정보를 가져올 수 없어 Jira 코멘트를 건너뜁니다.');
    process.exit(0);
  }
  const issueKey = (message.match(/([A-Z]+-\d+)/) || [])[1] || DEFAULT_ISSUE;
  const commentText = [
    `커밋 완료: ${hash.slice(0, 7)}`,
    `작성자: ${author}`,
    `일시: ${new Date(date).toLocaleString('ko-KR')}`,
    '',
    '**커밋 메시지:**',
    message,
    '',
    '**변경 통계:**',
    `+${stats.additions}줄 추가, -${stats.deletions}줄 삭제`,
    '',
    `**변경된 파일 (${files.length}개):**`,
    ...files.slice(0, 10).map((f) => `- ${f}`),
    ...(files.length > 10 ? [`... 외 ${files.length - 10}개 파일`] : []),
  ].join('\n');
  await addComment(issueKey, textToJiraBody(commentText));
  console.log(`✅ Jira 코멘트 추가 완료: ${issueKey}`);
}

async function commentCmd(issueKey, content) {
  if (!content) {
    console.error('Usage: node scripts/git/jira.mjs comment "내용" [--issue WEB-123]');
    console.error('   or: node scripts/git/jira.mjs comment @파일.txt [--issue WEB-123]');
    process.exit(1);
  }
  await addComment(issueKey, textToJiraBody(content));
  console.log(`✅ 코멘트 추가 완료: ${issueKey}`);
}

async function logCmd(issueKey, userReq, aiRes) {
  const user = readContent(userReq || '');
  const ai = readContent(aiRes || '');
  const timestamp = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  const content = [
    { type: 'heading', attrs: { level: 3 }, content: [{ type: 'text', text: `대화 기록 - ${timestamp}` }] },
    { type: 'paragraph', content: [{ type: 'text', text: '' }] },
    { type: 'heading', attrs: { level: 4 }, content: [{ type: 'text', text: '👤 사용자 요청' }] },
    { type: 'codeBlock', attrs: { language: 'plain' }, content: [{ type: 'text', text: ensureUtf8(user) }] },
    { type: 'paragraph', content: [{ type: 'text', text: '' }] },
    { type: 'heading', attrs: { level: 4 }, content: [{ type: 'text', text: '🤖 AI 응답' }] },
    ...ensureUtf8(ai)
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => ({ type: 'paragraph', content: [{ type: 'text', text: ensureUtf8(l) }] })),
  ];
  await addComment(issueKey, {
    body: { type: 'doc', version: 1, content },
  });
  console.log(`✅ 대화 기록 완료: ${issueKey}`);
}

async function summaryCmd(issueKey, filePath, inlineSummary) {
  let summary = inlineSummary ? readContent(inlineSummary) : '';
  if (filePath) summary = readFileSync(join(ROOT, filePath), 'utf-8').replace(/^\uFEFF/, '').trim();
  if (!summary) {
    console.error('Usage: node scripts/git/jira.mjs summary "요약" [--issue WEB-123]');
    console.error('   or: node scripts/git/jira.mjs summary --file 파일.txt [--issue WEB-123]');
    process.exit(1);
  }
  const doc = markdownToJiraDoc(summary);
  await addComment(issueKey, { body: doc });
  console.log(`✅ 작업 요약 기록 완료: ${issueKey}`);
}

async function deleteCmd(issueKey) {
  const res = await fetch(`${JIRA_URL}/rest/api/3/issue/${issueKey}/comment`, {
    headers: { Authorization: `Basic ${getAuth()}`, Accept: 'application/json' },
  });
  const data = await res.json();
  const comments = data.comments || [];
  if (!comments.length) {
    console.log('❌ 삭제할 코멘트가 없습니다.');
    return;
  }
  const latest = comments[comments.length - 1];
  const delRes = await fetch(
    `${JIRA_URL}/rest/api/3/issue/${issueKey}/comment/${latest.id}`,
    { method: 'DELETE', headers: { Authorization: `Basic ${getAuth()}`, Accept: 'application/json' } }
  );
  if (!delRes.ok) throw new Error(await delRes.text());
  console.log(`✅ 코멘트 삭제 완료: ${issueKey}`);
}

function createCommentFile() {
  const path = join(ROOT, 'jira-comment.txt');
  const template = `작업 요약을 여기에 작성하세요.

### 완료된 작업
- 작업 1
- 작업 2

### 다음 작업
- 작업 3
`;
  if (existsSync(path)) {
    console.log('현재 파일 내용:');
    console.log(readFileSync(path, 'utf-8').replace(/^\ufeff/, ''));
    console.log('\n저장 후: node scripts/git/jira.mjs summary --file jira-comment.txt --issue', DEFAULT_ISSUE);
  } else {
    writeFileSync(path, '\uFEFF' + template, 'utf-8');
    console.log(`✅ 파일 생성: ${path}`);
    console.log(`   저장 후: node scripts/git/jira.mjs summary --file jira-comment.txt --issue ${DEFAULT_ISSUE}`);
  }
}

async function main() {
  const { cmd, opts, rest } = parseArgs();
  const issueKey = opts.issue || DEFAULT_ISSUE;

  if (!cmd || cmd === 'help' || cmd === '--help' || cmd === '-h') {
    console.log(`
Jira 통합 스크립트

  post-commit               커밋 후 이슈에 코멘트 자동 추가 (기본 이슈 또는 커밋 메시지에서 추출)
  comment "내용"            코멘트 추가 (--issue WEB-123)
  comment @파일.txt
  log "사용자요청" "AI응답"  대화 기록 형식으로 코멘트 추가 (--issue WEB-123)
  summary "요약"             작업 요약 코멘트 (마크다운) (--issue WEB-123)
  summary --file 파일.txt
  delete                    최근 코멘트 삭제 (--issue WEB-123)
  create-comment-file       jira-comment.txt 템플릿 생성
`);
    process.exit(0);
  }

  try {
    switch (cmd) {
      case 'post-commit':
        await postCommit();
        break;
      case 'comment': {
        const content = rest[0] ? (rest[0].startsWith('@') ? readContent(rest[0]) : rest.join(' ')) : '';
        await commentCmd(issueKey, content);
        break;
      }
      case 'log':
        await logCmd(issueKey, rest[0], rest[1]);
        break;
      case 'summary':
        if (opts.file) await summaryCmd(issueKey, opts.file);
        else await summaryCmd(issueKey, null, rest[0] || '');
        break;
      case 'delete':
        await deleteCmd(issueKey);
        break;
      case 'create-comment-file':
        createCommentFile();
        break;
      default:
        console.error('알 수 없는 명령:', cmd);
        process.exit(1);
    }
  } catch (e) {
    console.error('❌', e.message);
    process.exit(1);
  }
}

main();
