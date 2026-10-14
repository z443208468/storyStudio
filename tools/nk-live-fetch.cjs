// P2-04 only: capture sanitized request identity and raw provider response in a private run.
const fs = require("node:fs");
const path = require("node:path");
const capturePath = process.env.STORYSTUDIO_NK_LIVE_CAPTURE;
const requestId = process.env.STORYSTUDIO_NK_LIVE_REQUEST_ID;
const inputTokenCapRaw = process.env.STORYSTUDIO_NK_MAX_INPUT_TOKENS;
if (!capturePath || !requestId) throw new Error("NK_LIVE_CAPTURE_CONFIG_REQUIRED");
const originalFetch = globalThis.fetch.bind(globalThis);

globalThis.fetch = async (input, init) => {
  const rawUrl = typeof input === "string" || input instanceof URL ? String(input) : input.url;
  const url = new URL(rawUrl);
  if (url.protocol === "http:" || url.protocol === "https:") {
    if (url.origin !== "https://api.deepseek.com" || url.pathname !== "/v1/chat/completions") {
      throw new Error("NK_LIVE_TEST_BLOCKED_UNEXPECTED_NETWORK_DESTINATION");
    }
  }

  let bodyText = init && init.body != null ? String(init.body) : "";
  if (!bodyText && input && typeof input.clone === "function") {
    bodyText = await input.clone().text();
  }
  let requestBody;
  try { requestBody = JSON.parse(bodyText); } catch { throw new Error("NK_LIVE_REQUEST_BODY_INVALID"); }
  if (requestBody.model !== "deepseek-flash" || requestBody.response_format?.type !== "json_object"
      || requestBody.reasoning_effort !== "none" || requestBody.max_tokens !== 512) {
    throw new Error("NK_LIVE_PROVIDER_CONFIG_INVALID");
  }

  const inputTokenCap = Number(inputTokenCapRaw);
  if (!/^[1-9][0-9]*$/.test(inputTokenCapRaw || "")
      || !Number.isSafeInteger(inputTokenCap) || inputTokenCap > 10000) {
    throw new Error("NK_LIVE_INPUT_CAP_INVALID");
  }
  if (!Array.isArray(requestBody.messages) || requestBody.messages.length === 0) {
    throw new Error("NK_LIVE_PROVIDER_MESSAGES_INVALID");
  }
  const estimatedInputTokens = Math.max(256, Array.from(JSON.stringify(requestBody.messages)).length + 256);
  if (estimatedInputTokens > inputTokenCap) {
    throw new Error("NK_LIVE_INPUT_LIMIT_EXCEEDED");
  }

  const response = await originalFetch(input, init);
  let providerResponse;
  try { providerResponse = await response.clone().json(); }
  catch { providerResponse = { response_unparsed: true }; }
  for (const choice of providerResponse.choices || []) {
    if (choice.message && Object.prototype.hasOwnProperty.call(choice.message, "reasoning_content")) {
      delete choice.message.reasoning_content;
    }
  }
  const record = {
    request_id: requestId,
    host: url.origin,
    path: url.pathname,
    status: response.status,
    requested_model: requestBody.model,
    response_format: requestBody.response_format.type,
    reasoning_effort: requestBody.reasoning_effort,
    max_output_tokens: requestBody.max_tokens,
    estimated_input_tokens: estimatedInputTokens,
    input_token_cap: inputTokenCap,
    reasoning_content_recorded: false,
    response: providerResponse,
  };
  fs.mkdirSync(path.dirname(capturePath), { recursive: true });
  fs.appendFileSync(capturePath, JSON.stringify(record) + "\n", { encoding: "utf8", mode: 0o600 });
  return response;
};
