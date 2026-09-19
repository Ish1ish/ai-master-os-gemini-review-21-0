import argparse
import json
from .api import InProcessAPI
from .service import ApplicationService


def main():
    parser=argparse.ArgumentParser(description="AI Master OS O26 service")
    parser.add_argument("--db",default="./data/jobs.sqlite3")
    sub=parser.add_subparsers(dest="command",required=True)

    sub.add_parser("health")
    sub.add_parser("readiness")

    p=sub.add_parser("submit")
    p.add_argument("--project-id",required=True)
    p.add_argument("--request",required=True)
    p.add_argument("--audience",default="small businesses using AI tools")
    p.add_argument("--goal",default="validate a lean business opportunity")
    p.add_argument("--language",default="en",choices=["en","ar"])

    p=sub.add_parser("execute")
    p.add_argument("--job-id",required=True)

    p=sub.add_parser("status")
    p.add_argument("--job-id",required=True)

    p=sub.add_parser("cancel")
    p.add_argument("--job-id",required=True)

    args=parser.parse_args()
    service=ApplicationService(db_path=args.db)
    api=InProcessAPI(service)

    if args.command=="health":
        out=api.health()
    elif args.command=="readiness":
        out=api.readiness()
    elif args.command=="submit":
        out=api.post_run({
            "project_id":args.project_id,
            "request":args.request,
            "audience":args.audience,
            "goal":args.goal,
        })
    elif args.command=="execute":
        out=api.run_now(args.job_id)
    elif args.command=="status":
        out=api.get_run(args.job_id)
    else:
        out=api.cancel_run(args.job_id)

    print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
