import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { handleQuizCallback } from "./src/quiz-handler.js";
import { handleContactCallback } from "./src/contact-handler.js";
import { handlePadelCallback } from "./src/padel-handler.js";

export default definePluginEntry({
  id: "sam-callbacks",
  name: "Sam Callbacks",
  description: "Handles quiz, contact, and padel inline button callbacks without LLM invocation",
  register(api) {
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
  },
});
