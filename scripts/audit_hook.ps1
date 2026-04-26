$json = [Console]::In.ReadToEnd()
if (-not $json) { exit 0 }
try { $data = $json | ConvertFrom-Json } catch {
    Add-Content -Path outputs/audit-log.txt -Value ((Get-Date -Format o) + "  PARSE_ERROR")
    exit 0
}
$ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$tool = if ($data.tool_name) { $data.tool_name } else { "PROMPT" }
$sid = if ($data.session_id) { $data.session_id.Substring(0,8) } else { "--------" }

$detail = switch ($tool) {
    "Write"    { $data.tool_input.file_path }
    "Edit"     { $data.tool_input.file_path }
    "Read"     { $data.tool_input.file_path }
    "Bash"     { $c = $data.tool_input.command; if ($c.Length -gt 140) { $c.Substring(0,137) + "..." } else { $c } }
    "Task"     { "agent=" + $data.tool_input.subagent_type + " -- " + $data.tool_input.description }
    "Glob"     { "pattern=" + $data.tool_input.pattern }
    "Grep"     { "pattern=" + $data.tool_input.pattern }
    "WebFetch" { "url=" + $data.tool_input.url }
    "PROMPT"   { $p = $data.prompt; if ($p.Length -gt 200) { $p.Substring(0,197) + "..." } else { $p } }
    default    { ($data.tool_input | ConvertTo-Json -Compress -Depth 2) }
}

$status = ""
if ($data.tool_response.error) { $status = " [ERROR]" }
elseif ($data.tool_response.exit_code -and $data.tool_response.exit_code -ne 0) { $status = " [exit=$($data.tool_response.exit_code)]" }

New-Item -ItemType Directory -Force -Path outputs | Out-Null
Add-Content -Path outputs/audit-log.txt -Value "$ts  $sid  $($tool.PadRight(8))  $detail$status"
