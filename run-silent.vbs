' Lance run.bat en arriere-plan sans afficher de fenetre cmd.
' A utiliser dans le Planificateur Windows pour les executions automatiques.
' Pour un lancement manuel avec console visible, utiliser run.bat directement.

Set WshShell = CreateObject("WScript.Shell")
' 0 = fenetre cachee, False = ne pas attendre la fin
WshShell.Run Chr(34) & WScript.ScriptFullName & "\..\run.bat" & Chr(34), 0, False
