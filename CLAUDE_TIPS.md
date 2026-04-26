Practical Tips for Claude Code on Data Projects
A reference of lessons learned during the fraud detection build. Drop into
the Medium article as a "Part 4" section, or keep separate as a project
appendix.
######################################################################
Prompting tips
#####################################################################
Anchor headline numbers in your prompt. When you ask Claude to write a
report or build a deck, name the number you want it to lead with. "Open
with: ROC-AUC 0.949, 96.8% of supervised performance" produces tighter
writing than "summarize the results." The model is good at execution; you
are good at framing — let each side play to its strength.
Cite output file paths explicitly. "Pull numbers from
outputs/ml/anomaly_metrics.csv" works far better than "use the metrics
file." If a prompt names a file by path, Claude reads it before writing. If
it just says "the metrics," it sometimes invents plausible-looking numbers.
Block accidental re-runs of expensive skills. Claude's skill router
defaults to the top-level skill on ambiguous prompts. If you only want a
sub-skill to fire, say so explicitly: "Do NOT invoke the fraud-analyst
skill. Invoke ONLY the interview-deck skill." That one sentence saved me
a 30-minute accidental re-run.
Run the cheapest prompt first. When you can, sketch the answer with a
small prompt before authorizing the expensive one. "What would the
structure of this analysis look like?" is roughly a $0.01 question.
Spending three minutes on it can save thirty minutes of wrong-direction
work.
#######################################################################
Project-structure tips
####################################################################
One CLAUDE.md per project, kept under 200 lines. This file is your
project's standing instructions — conventions, file paths, allowed
libraries, security rules, output layout. Claude reads it at the start of
every session. Keep it short and concrete; a 1,000-line CLAUDE.md gets
ignored in practice.
One agent per responsibility. Each agent file should have a single
verb in its description: "profile the data," "train the models," "write
the report." If you find yourself writing "and also" in an agent's
description, split it into two agents. Specialists outperform generalists,
even at AI scale.
Stamp every run. A timestamped output directory with input hash,
library versions, and git SHA costs nothing to set up and makes the
difference between "we have an ML system" and "we have an auditable ML
system." Especially in regulated industries, this is the difference
between a demo and a deployment.
Write Python to files, never inline python -c. PowerShell mangles
multi-line quoted commands. The agent will sometimes try a one-liner, fail
with a confusing quoting error, and waste tokens debugging itself. Tell it
once, in CLAUDE.md, to always use .py files for anything longer than a
single line.

##########################################################################
Safety and controls
##########################################################################
The tools list is your security perimeter. Each agent declares which
tools it can use in its YAML header. An agent without Bash cannot run
shell commands. An agent without WebFetch cannot reach the internet.
Give agents the minimum tools they need, and sleep better.
Use the allow / deny pattern in settings.local.json. Allow the
specific commands you trust (Bash(python:*), Bash(pip:*),
Bash(mkdir:*)); deny the dangerous ones (Bash(curl:*), Bash(rm:*),
Bash(git push:*)). The few minutes it takes to write a deny list pays
back the first time the model tries to do something you do not want.
Hooks are how you bolt policy onto an AI. A one-line PowerShell hook
gives you a complete audit log of every file write and every shell
command. If something goes wrong, you can replay it. If a regulator asks
for evidence, you have it. Hooks fire on every tool call whether you are
watching or not.
Never paste secrets into a chat or a settings file. Tokens, API keys,
passwords — these go in environment variables, and .env goes in
.gitignore on day one. If you accidentally paste a token, rotate it
immediately. The chat log is not private from the model's training
pipeline.

######################################################################
Cost and quota management
######################################################################
Use /agents and /doctor before any long run. These two slash
commands cost essentially nothing and catch configuration bugs that would
otherwise waste twenty minutes. /agents lists every agent that loaded
successfully. /doctor flags missing tools, broken settings, or unset
environment variables.
Watch the runtime, not just the result. A 30-minute run is normal for
a full pipeline. A 60-minute run almost always means the agent is stuck in
a debugging loop and burning tokens. If you see a single agent over 15
minutes, hit Esc, read what it is doing, and unblock it manually.
Know about /rate-limit-options. Three options when you hit your
quota: stop and wait for reset, switch to extra usage (paid), or upgrade
the plan. For most personal projects, "stop and wait" is the right answer
— quotas reset hourly or daily.
Save final-touch prompts for after the heavy work. If you have only
20% of your quota left, do not start a fresh pipeline run. Use the
remaining tokens for cheap polish prompts ("rewrite this paragraph,"
"build a deck from existing files") that finish the deliverable rather
than starting a new one.

###################################################################
Common pitfalls
###################################################################
Sub-agents do not share context with the parent. Each invocation of a
sub-agent starts a fresh conversation. If the parent learned something
useful, that information is gone unless it was written to a file. Pass
context through files (CLAUDE.md, run summaries, parquet outputs), not
through chat history.
The CLAUDE.md is read at session start. If you edit it mid-session,
the changes will not take effect until you /clear or restart Claude.
Get into the habit of editing CLAUDE.md and immediately running /clear
to refresh.
A successful tool call is not a successful task. The agent might write
a Python file, run it, get an error, and silently move on. Always read the
final summary critically — does it cite numbers from real files, or does
it gloss past errors with vague language? "I encountered some issues" is
the model's tell that something failed.
Plan mode (Shift+Tab to toggle) for any task with more than three
steps. It surfaces the plan before any tool calls happen, so you can
catch a wrong assumption before it costs anything.

Slash command cheat sheet
CommandWhat it does/agentsList all sub-agents available in this project
/doctorRun diagnostics — settings, environment, MCP servers
/mcpShow MCP server status
/clearWipe the conversation context (forces CLAUDE.md to reload)
/resumeContinue a previous session/rate-limit-optionsTriggered when you hit your quota
/planEnter plan mode (alternative: Shift+Tab)
/helpFull command list
##############################################################
Keyboard shortcuts worth memorizing
#####################################################
Shift+Tab Toggle accept-edits mode (auto-approve safe edits)
Esc Cancel the current tool call without losing context
Ctrl+O Expand truncated output in the terminalUp arrowRecall previous prompt
Ctrl+C Exit Claude