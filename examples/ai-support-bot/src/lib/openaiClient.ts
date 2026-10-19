import OpenAI from "openai";
import { SYSTEM_PROMPT } from "../prompts/systemPrompt";

const DEFAULT_MODEL = "gpt-4o-mini";
const FALLBACK_MODEL = "gpt-3.5-turbo";

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function chatCompletion(userMessage: string) {
  const res = await client.chat.completions.create({
    model: DEFAULT_MODEL,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: userMessage },
    ],
  });
  return res.choices[0]?.message?.content ?? "";
}
