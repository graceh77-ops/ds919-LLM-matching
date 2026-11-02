# DeepSeek weight elicitation for propensity-score-augmented matching

Use this workflow to elicit one new 12-score weight set specifically for the
propensity-score-augmented matching comparison. It does not replace or
overwrite earlier DeepSeek weights. The saved run folder is separate under
`results/ps_augmented_matching/deepseek_api/`.

The API script sends only the delimited prompt body from
[`weight_prompt_evidence_focused.md`](weight_prompt_evidence_focused.md). It does not load cohort data, prior
weights, matching outputs, or empirical evaluation results. Each API call is
a separate request with no conversation history.

This prompt uses the required integer 0-to-10 schema and matching weight
direction; do not use the Lasso paper's 0.1-to-1 inverse-penalty scores
directly as distance weights.

From a PowerShell terminal at the repository root, run:

```powershell
Set-Location "cdc natality"
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "DeepSeek API key" -AsSecureString)).Password
python src/get_deepseek_weights.py `
  --prompt docs/ps_augmented_matching/weight_prompt_evidence_focused.md `
  --output-root results/ps_augmented_matching/deepseek_api `
  --schema ps-augmented
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

The `ps-augmented` schema requires the eleven covariate keys plus
`PROPENSITY_SCORE`. The older `ps-residual` schema label remains a compatible
alias. Those scores now
map to original encoded covariate columns and the appended probability
coordinate; there is no residualization. The current implementation uses a
single non-streaming JSON-mode request,
temperature 0, thinking disabled, and a 512-token output limit. The default
model is selected by the extraction script; check current provider settings
before requesting another run.
