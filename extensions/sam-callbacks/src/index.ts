import { handleQuizCallback } from "./quiz-handler.js";
import { handleContactCallback } from "./contact-handler.js";

export default function register(api: any) {
  // Quiz callbacks: quiz:taskId|action|value
  api.registerInteractiveHandler({
    channel: "telegram",
    namespace: "quiz",
    handler: async (ctx: any) => {
      return handleQuizCallback(ctx.callback.payload, ctx.respond);
    },
  });

  // Contact callbacks: contact:taskId|action
  api.registerInteractiveHandler({
    channel: "telegram",
    namespace: "contact",
    handler: async (ctx: any) => {
      return handleContactCallback(ctx.callback.payload, ctx.respond);
    },
  });
}
