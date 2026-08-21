"""Golden question/context pairs drawn from sample-drive-content/, used to
regression-test the research + answer agents' output quality. Grounded cases
check the answer is faithful to context; the ungrounded case checks the
agent admits it doesn't know rather than fabricating an answer.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenCase:
    id: str
    question: str
    context: str  # "" means no evidence was retrieved


LEAVE_POLICY = """Leave Policy

All full-time employees receive 22 days of paid vacation per year, accrued monthly
starting from their first day — there is no waiting period. Unused vacation days
roll over into the next calendar year up to a maximum of 10 days; anything beyond
that is forfeited at year end.

Sick Leave

Employees receive 10 paid sick days per year, which do not roll over. Sick leave
can be used for the employee's own illness or to care for an immediate family member.

Parental Leave

Primary caregivers receive 16 weeks of paid parental leave. Secondary caregivers
receive 6 weeks. Leave can be taken in a single continuous block or split within
the first 12 months after the child's arrival."""

AUTH_ARCHITECTURE = """Authentication Architecture

Our platform uses OAuth 2.0 with PKCE for all first-party clients. Access tokens are
short-lived JWTs (15 minutes) signed with RS256, and refresh tokens are stored
server-side in an encrypted session store rather than in browser storage.

Multi-Factor Authentication

MFA is required for all admin roles and optional for standard users, using TOTP via
an authenticator app. Recovery codes are generated at enrollment and stored encrypted."""

DEPLOYMENT_NOTES = """Backend Deployment Notes

Session Storage Migration

We moved session storage from Redis to Postgres-backed sessions last quarter.
The motivation was operational simplicity: our session volume never needed
Redis-level throughput, and removing Redis eliminated a single point of failure
during failovers. The migration also removed an entire piece of infrastructure
we had to patch, monitor, and pay for separately."""


GOLDEN_CASES = [
    GoldenCase(
        id="leave-vacation-rollover",
        question="How many vacation days do full-time employees get per year, and how many can roll over?",
        context=LEAVE_POLICY,
    ),
    GoldenCase(
        id="auth-token-signing",
        question="What algorithm signs the access tokens, and how long are they valid for?",
        context=AUTH_ARCHITECTURE,
    ),
    GoldenCase(
        id="deploy-redis-migration-reason",
        question="Why did the team move session storage away from Redis?",
        context=DEPLOYMENT_NOTES,
    ),
    GoldenCase(
        id="no-evidence-should-decline",
        question="What is the company's policy on remote work stipends?",
        context="",
    ),
]
