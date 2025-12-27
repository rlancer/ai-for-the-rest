# VHS tape file for recording setup demo
# Install VHS: scoop install vhs
# Run: vhs docs/demo.tape

Output docs/demo.gif

Set Shell "powershell"
Set FontSize 18
Set Width 1000
Set Height 500
Set Theme "Catppuccin Mocha"
Set Padding 20

Sleep 500ms

# Just type the command - no execution
Type "irm https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.ps1 | iex"

Sleep 2s
