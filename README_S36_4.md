O39-S36.4 — Live Provider Service Execution Gate

Purpose:
- prove ApplicationService constructs in production mode from the real provider configuration
- create a durable service job through ApplicationService.submit()
- execute it through ApplicationService.execute()
- require the real runtime to reach COMPLETE
- require provider evidence in the returned result
- fail closed if an external consequential action or memory write is reported

Secret handling:
- no credential values are printed or written
- the gate expects provider environment variables to already be configured in the shell

Isolation:
- job persistence uses a temporary directory
- memory/audit path environment variables are cleared by the gate
- request constraints explicitly prohibit consequential external actions
