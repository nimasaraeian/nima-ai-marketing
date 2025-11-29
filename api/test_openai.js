/**
 * Fresh OpenAI API test - Node.js version
 */
import OpenAI from "openai";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env from project root
dotenv.config({ path: join(__dirname, "..", ".env") });

const apiKey = process.env.OPENAI_API_KEY;

console.log("=".repeat(60));
console.log("FRESH OPENAI API TEST (Node.js)");
console.log("=".repeat(60));
console.log();

if (!apiKey) {
    console.error("[ERROR] OPENAI_API_KEY not found in .env");
    process.exit(1);
}

if (!apiKey.startsWith("sk-")) {
    console.error(`[ERROR] API key doesn't start with 'sk-': ${apiKey.substring(0, 10)}...`);
    process.exit(1);
}

console.log(`[OK] API Key found: ${apiKey.substring(0, 25)}...${apiKey.substring(apiKey.length - 15)}`);
console.log();

const client = new OpenAI({ apiKey });

console.log("Testing API connection...");
console.log("-".repeat(60));
console.log();

try {
    const response = await client.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
            { role: "user", content: "Say OK if API is working." }
        ],
        max_tokens: 10
    });

    const output = response.choices[0].message.content;
    
    console.log("=".repeat(60));
    console.log("[SUCCESS] API OK!");
    console.log("=".repeat(60));
    console.log(`Response: ${output}`);
    console.log();
    
} catch (error) {
    console.log("=".repeat(60));
    
    if (error.status === 429) {
        console.log("[ERROR] RATE LIMIT / QUOTA ERROR");
        console.log("=".repeat(60));
        console.log(`Error: ${error.message}`);
        console.log();
        console.log("Possible causes:");
        console.log("  - Quota exceeded");
        console.log("  - Rate limit reached");
        console.log("  - API key not activated");
    } else if (error.status === 401) {
        console.log("[ERROR] AUTHENTICATION ERROR");
        console.log("=".repeat(60));
        console.log(`Error: ${error.message}`);
        console.log();
        console.log("Check:");
        console.log("  - API key is correct");
        console.log("  - API key is active");
    } else {
        console.log("[ERROR] UNEXPECTED ERROR");
        console.log("=".repeat(60));
        console.log(`Error Type: ${error.constructor.name}`);
        console.log(`Error: ${error.message}`);
    }
    
    console.log();
}

console.log("=".repeat(60));




