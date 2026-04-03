import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { handleQuizCallback } from "./src/quiz-handler.js";
import { handleContactCallback } from "./src/contact-handler.js";
import { handlePadelCallback } from "./src/padel-handler.js";
import { handleAskFelixWebhook, handleVpCallback } from "./src/askfelix-handler.js";

export default definePluginEntry({
  id: "sam-callbacks",
  name: "Sam Callbacks",
  description: "Handles quiz, contact, padel, and askFelix callbacks + webhook",
  register(api) {
    // ── Interactive handlers (Telegram buttons) ──

    api.registerInteractiveHandler({
      channel: "telegram",
      namespace: "quiz",
      handler: async (ctx) => {
        return handleQuizCallback(ctx.callback.payload, ctx.respond);
      },
    });

    api.registerInteractiveHandler({
      channel: "telegram",
      namespace: "contact",
      handler: async (ctx) => {
        return handleContactCallback(ctx.callback.payload, ctx.respond);
      },
    });

    api.registerInteractiveHandler({
      channel: "telegram",
      namespace: "padel",
      handler: async (ctx) => {
        return handlePadelCallback(ctx.callback.payload, ctx.respond);
      },
    });

    // askFelix: Retell mid-call asks Felix which time to pick
    api.registerInteractiveHandler({
      channel: "telegram",
      namespace: "vp",
      handler: async (ctx) => {
        return handleVpCallback(ctx.callback.payload, ctx.respond);
      },
    });

    // ── HTTP route: askFelix webhook (Retell calls this mid-call) ──

    api.registerHttpRoute({
      path: "/webhook/ask-felix",
      handler: handleAskFelixWebhook,
      auth: "plugin",  // No gateway auth needed - Retell calls this
    });
  },
});
