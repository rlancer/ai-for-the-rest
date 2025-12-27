# VHS tape file for recording setup demo
# Run: vhs docs/demo.tape

Output docs/demo.gif

Set FontSize 20
Set Width 900
Set Height 300
Set Theme "Catppuccin Mocha"
Set Padding 20

Sleep 500ms

Type "irm https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.ps1 | iex"

Sleep 2s
