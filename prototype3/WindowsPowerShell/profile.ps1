
#region conda initialize
# !! Contents within this block are managed by 'conda init' !!
If (Test-Path "C:\anaconda\Scripts\conda.exe") {
    (& "C:\anaconda\Scripts\conda.exe" "shell.powershell" "hook") | Out-String | ?{$_} | Invoke-Expression
}
#endregion

