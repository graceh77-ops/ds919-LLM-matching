# DeepSeek API weight elicitation setup

## Purpose and separation

This script requests one outcome-blind set of covariate-priority weights from
DeepSeek. It sends only the text between the delimiters in
[`llm_prompt_covariate_weights.md`](llm_prompt_covariate_weights.md). It does
not load the natality cohort, previous weights, matching outputs, or evaluation 
metrics.

## Local setup

1. Create an API key through your DeepSeek account. Keep the key private. If a
   key was exposed, revoke it and use a newly created key.
2. In a PowerShell terminal opened at the project root, set the key for that
   terminal session. This prompts without echoing the key as you type or paste:

   ```powershell
   $env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "DeepSeek API key" -AsSecureString)).Password
   ```

   The key is not saved in the repository.
3. Run exactly one elicitation:

   ```powershell
   python src/get_deepseek_weights.py
   ```

   After the request, remove the key from that terminal session:

   ```powershell
   Remove-Item Env:DEEPSEEK_API_KEY
   ```

   The default model is `deepseek-flash`. To select another currently available
   model, set `DEEPSEEK_MODEL` before running.
4. Keep the terminal open until it reports success or an error. A successful
   run writes a timestamped folder under
   `results/manual llm matching/deepseek_api/` with the validated weights, raw
   API response, raw model text, exact prompt, and request metadata.
5. Review the saved record and weights before using them in matching. Do not
   change the scores manually. If the response fails validation, the raw output
   is retained; record any later retry as a separate elicitation.

The script makes a single non-streaming request, with JSON output enabled,
thinking disabled, temperature set to 0, and a 512-token output limit. It does
not retry automatically, avoiding accidental duplicate API calls or charges.
It refuses to overwrite a timestamped run folder.

## Current API settings

The integration uses the official DeepSeek chat completions endpoint at
`https://api.deepseek.com/chat/completions` and the model name
`deepseek-flash`. DeepSeek's model and pricing page identifies the current
underlying model version; the response's returned model is also saved in each
run record. These names and versions can change, so verify DeepSeek's official
documentation before later reruns.

## References

- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [DeepSeek JSON Output guide](https://api-docs.deepseek.com/guides/json_mode/)
- [DeepSeek Models and Pricing](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek API authentication](https://api-docs.deepseek.com/api/deepseek-api/)
