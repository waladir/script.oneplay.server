## Summary
Po přechodu OnePlay na API v1.11 selhával login u účtů s více službami (ShowAccountChooserStep).

## Problém
- KeyError: 'accounts' — nové API vrací účty v step.groups[].accounts
- v logu systemd Python traceback místo srozumitelné chyby
- TVHeadend opakovaně volal login → rate limit OnePlay API

## Oprava
- parsování step.groups[].accounts
- OneplayError + log_error() místo sys.exit()
- Bottle plugin pro čitelné chyby v journalu
- cooldown 5 min po neúspěšném loginu
- .gitignore pro config.txt a runtime data

## Testováno
- login s více službami (poradi_sluzby)
- /playlist, /epg, /play redirect 303, TVHeadend
