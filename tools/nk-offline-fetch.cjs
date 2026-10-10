const crypto = require('node:crypto');
const fs = require('node:fs');
const originalFetch = globalThis.fetch;
const expectedHost = 'https://api.deepseek.com/v1/chat/completions';
const capturePath = process.env.STORYSTUDIO_NK_OFFLINE_CAPTURE;
const fixturePath = process.env.STORYSTUDIO_NK_OFFLINE_FIXTURE;
if (process.env.STORYSTUDIO_NK_OFFLINE_TEST !== '1' || !capturePath || !fixturePath) {
  throw new Error('NK_OFFLINE_PRELOADER_REQUIRES_EXPLICIT_TEST_MODE');
}
const fixture = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
globalThis.fetch = async (input, init = {}) => {
  const url = typeof input === 'string' ? input : input.url;
  if (url === expectedHost) {
    const request = JSON.parse(init.body || '{}');
    const prompt = (request.messages || []).map((m) => m.content || '').join('\n');
    const cases = ['TOO_FEW', 'EMPTY', 'MALFORMED', 'TRUNCATED'];
    const mode = cases.find((key) => prompt.includes('OFFLINE_CASE_' + key)) || 'GOOD';
    const validRequest = request.model === 'deepseek-flash' && request.response_format?.type === 'json_object';
    const capture = {
      host: 'https://api.deepseek.com/v1',
      model: request.model || null,
      response_format: request.response_format?.type || null,
      prompt_sha256: crypto.createHash('sha256').update(prompt).digest('hex').toUpperCase(),
      prompt_length: prompt.length,
      case: mode,
      config_valid: validRequest,
    };
    fs.appendFileSync(capturePath, JSON.stringify(capture) + '\n');
    if (!validRequest) return Response.json({ error: { message: 'Expected DeepSeek Flash JSON mode' } }, { status: 400 });
    let content;
    if (mode === 'TOO_FEW') content = JSON.stringify({ perspectives: [] });
    else if (mode === 'EMPTY') content = JSON.stringify({ perspectives: [{ reflection: '' }] });
    else if (mode === 'MALFORMED') content = '{"perspectives": nope}';
    else if (mode === 'TRUNCATED') content = '{"perspectives":[{"reflection":"unfinished"';
    else content = JSON.stringify(fixture);
    return Response.json({
      id: 'offline-' + mode.toLowerCase(),
      object: 'chat.completion',
      created: 1,
      model: 'deepseek-flash',
      choices: [{ index: 0, message: { role: 'assistant', content }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 20, completion_tokens: 14, total_tokens: 34 },
    });
  }
  if (/^https?:/i.test(url)) throw new Error('OFFLINE_TEST_BLOCKED_NETWORK:' + new URL(url).host);
  return originalFetch(input, init);
};
