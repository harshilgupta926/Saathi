export async function readBoundedJson(request, maxBytes = 4096, timeoutMs = 5000) {
  const declaredHeader = request.headers.get("content-length");
  if (declaredHeader !== null) {
    if (!/^\d+$/.test(declaredHeader)) return { ok: false, status: 400, detail: "invalid_json" };
    if (Number(declaredHeader) > maxBytes) return { ok: false, status: 413, detail: "request_body_too_large" };
  }
  if (!request.body) return { ok: false, status: 400, detail: "invalid_json" };

  const reader = request.body.getReader();
  const chunks = [];
  let total = 0;
  const deadline = Date.now() + timeoutMs;
  try {
    while (true) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) {
        await reader.cancel().catch(() => undefined);
        return { ok: false, status: 408, detail: "request_body_timeout" };
      }
      let timer;
      let next;
      try {
        next = await Promise.race([
          reader.read(),
          new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error("request_body_timeout")), remaining);
          }),
        ]);
      } catch (error) {
        if (error instanceof Error && error.message === "request_body_timeout") {
          await reader.cancel().catch(() => undefined);
          return { ok: false, status: 408, detail: "request_body_timeout" };
        }
        return { ok: false, status: 400, detail: "invalid_json" };
      } finally {
        clearTimeout(timer);
      }
      const { done, value } = next;
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) {
        await reader.cancel().catch(() => undefined);
        return { ok: false, status: 413, detail: "request_body_too_large" };
      }
      chunks.push(value);
    }
  } catch {
    return { ok: false, status: 400, detail: "invalid_json" };
  } finally {
    try { reader.releaseLock(); } catch { /* already cancelled */ }
  }

  try {
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    const value = JSON.parse(decoded);
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return { ok: false, status: 400, detail: "json_object_required" };
    }
    return { ok: true, value };
  } catch {
    return { ok: false, status: 400, detail: "invalid_json" };
  }
}