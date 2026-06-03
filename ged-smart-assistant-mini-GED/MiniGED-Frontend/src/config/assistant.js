const rawAssistantUrl = import.meta.env.VITE_ASSISTANT_URL;

if (!rawAssistantUrl) {
  throw new Error("Missing VITE_ASSISTANT_URL in frontend environment");
}

const ASSISTANT_URL = rawAssistantUrl.replace(/\/$/, "");
const ASSISTANT_ORIGIN = new URL(ASSISTANT_URL).origin;
const ASSISTANT_SOURCE_SYSTEM = import.meta.env.VITE_ASSISTANT_SOURCE_SYSTEM || "mini-ged";

export { ASSISTANT_ORIGIN, ASSISTANT_SOURCE_SYSTEM, ASSISTANT_URL };
