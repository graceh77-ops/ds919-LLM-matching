# DeepSeek weight elicitation for PS-residual matching

Use this workflow to elicit one new 12-score weight set specifically for the
PS-residual matching comparison. It does not replace or overwrite earlier
DeepSeek weights. The saved run folder is separate under
`results/ps_residual_matching/deepseek_api/`.

The API script sends only the delimited prompt body from
[`weight_prompt.md`](weight_prompt.md). It does not load cohort data, prior
weights, matching outputs, or empirical evaluation results. Each API call is
a separate request with no conversation history.

From a PowerShell terminal at the repository root, run:

```powershell
Set-Location "cdc natality"
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "DeepSeek API key" -AsSecureString)).Password
python src/get_deepseek_weights.py `
  --prompt docs/ps_residual_matching/weight_prompt.md `
  --output-root results/ps_residual_matching/deepseek_api `
  --schema ps-residual
Remove-Item Env:DEEPSEEK_API_KEY
```

Wait for the script to print its saved run-folder path before removing the key.
If it reports an error, inspect the message and saved response before deciding
whether to retry; each retry creates a separate elicitation record.

The timestamped run folder contains the validated 12-score `weights.json`, the raw API
response, raw model text, and `record.md` with the exact prompt, requested and
returned model, response metadata, and prompt hash. Use that run's
`weights.json` with `--weights-json` when running the comparison. Do not edit
the returned scores manually.

The `ps-residual` schema requires the eleven covariate keys plus
`PROPENSITY_SCORE`. The current implementation uses a single non-streaming JSON-mode request,
temperature 0, thinking disabled, and a 512-token output limit. The default
model is selected by the extraction script; check current provider settings
before requesting another run.
