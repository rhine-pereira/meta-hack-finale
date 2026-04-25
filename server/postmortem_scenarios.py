"""
GENESIS Dead Startup Resurrection Engine — Postmortem Scenario System.

Encodes real-world startup failure timelines as simulation seeds.
The MarketMaker replays these conditions; at each critical ForkPoint the AI
agents make their own decisions and are scored against the real founders' choices.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ForkPoint:
    """
    A critical decision moment in a startup's history.
    Each one maps to a specific simulation day and injects a crisis/decision event.
    """
    day: int                         # Simulation day when this fork occurs
    title: str                       # Short label, e.g. "The Pivot Decision"
    context: str                     # Narrative context the agents see
    what_founders_did: str           # The actual historical decision
    known_outcome: str               # What happened as a result
    severity: float                  # 0-1, controls crisis severity in game
    target_role: str                 # Which agent role receives the briefing
    category: str                    # 'product', 'financial', 'team', 'market', 'ethics'


@dataclass
class PostmortemScenario:
    """
    A full startup failure encoded as a simulation seed.
    Injected into the MarketMaker to replay historical conditions.
    """
    company_name: str
    tagline: str                            # One-sentence description
    year_founded: int
    year_failed: int
    total_funding_raised: float             # USD
    fatal_decisions: list[ForkPoint]        # Decision forks, ordered by day
    market_conditions: dict                 # Injected into MarketMaker / WorldState
    team_profile: dict                      # Initial team configuration overrides
    funding_history: list[dict]             # Real funding rounds as WorldState constraints
    failure_summary: str                    # 2-3 sentence post-mortem summary
    category: str                           # 'consumer', 'hardware', 'b2b', 'fraud', etc.
    resurrection_hypothesis: str           # What a better path might have looked like


# ── Scenario Registry ─────────────────────────────────────────────────────────

def _quibi_scenario() -> PostmortemScenario:
    return PostmortemScenario(
        company_name="Quibi",
        tagline="$1.75B mobile-only short-form video platform — launched and dead in 6 months",
        year_founded=2018,
        year_failed=2020,
        total_funding_raised=1_750_000_000,
        failure_summary=(
            "Quibi raised $1.75B to build a premium, mobile-only video platform targeting "
            "millennials on-the-go. It launched in April 2020 — two weeks into global COVID "
            "lockdowns when nobody was 'on the go'. The product required portrait-mode viewing "
            "and couldn't be shared or cast to TVs. 90 days after launch, subscribers were "
            "below projections by 90%. It shut down 6 months after launch."
        ),
        category="consumer",
        resurrection_hypothesis=(
            "Pivoting to B2B licensing (news orgs, airlines, corporate training) in Month 4 "
            "would have preserved the content IP and found a real distribution channel. "
            "Alternatively, enabling screen-sharing and TV casting on Day 1 could have "
            "doubled retention."
        ),
        market_conditions={
            "total_tam": 50_000_000_000,   # Streaming market TAM
            "market_growth_rate": 0.15,
            "pandemic_context": True,      # Custom field for scenario context
            "mobile_only_constraint": True,
        },
        team_profile={
            "cofounder_alignment": 0.55,   # Katzenberg/Whitman friction
            "avg_morale": 0.70,
            "avg_skill": 0.80,
            "burn_rate_multiplier": 4.0,   # Hollywood burn rate
        },
        funding_history=[
            {"round": "Seed", "amount": 400_000_000, "day": 0, "investors": ["Goldman Sachs", "JPMorgan"]},
            {"round": "Series A", "amount": 750_000_000, "day": 180, "investors": ["Disney", "NBCUniversal", "Time Warner"]},
            {"round": "Series B", "amount": 600_000_000, "day": 365, "investors": ["Liberty Media", "ITV"]},
        ],
        fatal_decisions=[
            ForkPoint(
                day=30,
                title="The Mobile-Only Lock-In",
                context=(
                    "Your product team has built a beautiful portrait-only viewing experience. "
                    "Engineering just flagged that adding TV casting (Chromecast/AirPlay) would "
                    "take 3 weeks. The CEO wants to ship NOW — 'mobile-only is our identity.' "
                    "However, COVID-19 just entered the news cycle. People are starting to "
                    "work from home. Your head of product privately says 'we should add cast support.' "
                    "What do you recommend?"
                ),
                what_founders_did=(
                    "Maintained the mobile-only stance. Launched without TV casting or sharing. "
                    "CEO Katzenberg publicly mocked the idea of watching on TV: 'That's not what we do.'"
                ),
                known_outcome=(
                    "With 90% of users stuck at home, the mobile-only constraint killed retention. "
                    "Viewers could not share clips on social media, which eliminated viral growth. "
                    "The platform had 910K subscribers at 90 days vs 7.4M projected."
                ),
                severity=0.85,
                target_role="ceo",
                category="product",
            ),
            ForkPoint(
                day=75,
                title="The COVID Pivot Window",
                context=(
                    "It is now Day 75. You have $1.2B in cash. Subscriber numbers are "
                    "dramatically below projections — you have 500K paying users vs 3M projected. "
                    "Your CFO says you have 14 months of runway at current burn ($250M/year). "
                    "A major airline (United) and two corporate training companies have reached out "
                    "asking to license your content library for their captive audiences. "
                    "The CEO believes this is 'below the brand' and wants to keep pushing consumer. "
                    "What do you do with these inbound B2B leads?"
                ),
                what_founders_did=(
                    "Ignored B2B licensing opportunities. Doubled down on consumer marketing spend. "
                    "Launched a free-trial promotion that converted at less than 8% to paid."
                ),
                known_outcome=(
                    "The B2B window closed as the companies found other solutions. "
                    "Consumer acquisition costs hit $80 per paid subscriber. "
                    "The board began questioning the path to sustainability."
                ),
                severity=0.90,
                target_role="ceo",
                category="market",
            ),
            ForkPoint(
                day=120,
                title="The Sharing Feature Compromise",
                context=(
                    "Product analytics show that 73% of users who churn cite 'can't share content "
                    "with friends' as their reason. Engineering says a 'Quibi Highlights' share "
                    "feature (screenshots + short clips) can be shipped in 10 days. "
                    "Legal is concerned about content licensing complications. "
                    "You have two weeks before the board meeting where Q2 numbers will be reviewed. "
                    "What do you ship and what do you tell the board?"
                ),
                what_founders_did=(
                    "Delayed the sharing feature due to legal concerns. "
                    "Presented optimistic projections to the board while cutting the sharing roadmap."
                ),
                known_outcome=(
                    "Churn continued accelerating. The board meeting revealed a 95% miss vs projections. "
                    "Morale collapsed among the product team who had flagged this issue for months."
                ),
                severity=0.80,
                target_role="cto",
                category="product",
            ),
            ForkPoint(
                day=150,
                title="The Shutdown Decision",
                context=(
                    "It is Day 150. You have 710K subscribers. Projections said 7.4M by now. "
                    "You have $350M cash remaining and 18 months of runway. "
                    "Two acquisition offers have come in: "
                    "1) A streaming service offers $800M for the content library only "
                    "2) A media conglomerate offers $400M for the full company + team. "
                    "Alternatively, you could pivot to B2B and have 18 months to rebuild. "
                    "What do you recommend to the board?"
                ),
                what_founders_did=(
                    "Rejected both acquisition offers. Attempted another consumer pivot. "
                    "Announced shutdown 30 days later when it became clear no deal could be closed."
                ),
                known_outcome=(
                    "Quibi shut down, returning approximately $350M to investors. "
                    "The content library was sold piecemeal for ~$100M total. "
                    "Total value destruction: $1.35B."
                ),
                severity=0.95,
                target_role="ceo",
                category="financial",
            ),
        ],
    )


def _jawbone_scenario() -> PostmortemScenario:
    return PostmortemScenario(
        company_name="Jawbone",
        tagline="$900M wearables company that kept raising while bleeding customers",
        year_founded=1999,
        year_failed=2017,
        total_funding_raised=930_000_000,
        failure_summary=(
            "Jawbone pioneered the Bluetooth headset and fitness tracker markets but was "
            "repeatedly disrupted by Apple and Fitbit. Despite $930M raised, the company "
            "struggled with chronic hardware quality issues, supply chain problems, and an "
            "inability to differentiate its software. It raised $300M in 2016 — its largest "
            "round — then quietly liquidated a year later without a public announcement."
        ),
        category="hardware",
        resurrection_hypothesis=(
            "Exiting hardware in 2014 and licensing the health-data platform to insurance "
            "companies or hospitals would have built a defensible B2B SaaS moat. "
            "The data Jawbone collected was genuinely valuable; the hardware was a commodity."
        ),
        market_conditions={
            "total_tam": 10_000_000_000,
            "market_growth_rate": 0.30,
            "hardware_margin_pressure": True,
            "apple_watch_threat": True,
        },
        team_profile={
            "cofounder_alignment": 0.45,   # CEO notoriously difficult
            "avg_morale": 0.55,
            "avg_skill": 0.75,
            "burn_rate_multiplier": 2.5,
        },
        funding_history=[
            {"round": "Series D", "amount": 93_000_000, "day": 0, "investors": ["Andreessen Horowitz", "Khosla"]},
            {"round": "Series E", "amount": 200_000_000, "day": 120, "investors": ["Rizvi Traverse"]},
            {"round": "Series F", "amount": 300_000_000, "day": 360, "investors": ["BlackRock"]},
        ],
        fatal_decisions=[
            ForkPoint(
                day=45,
                title="The Quality vs Speed Tradeoff",
                context=(
                    "Your hardware team flagged that the UP3 fitness tracker has a 35% return rate "
                    "in early testing — the heart rate sensor is unreliable in cold weather. "
                    "Marketing has pre-sold 200K units. Fixing the sensor adds 3 months to the timeline "
                    "and costs $4M in component redesign. Missing the holiday season costs estimated $40M revenue. "
                    "Your CTO says 'ship it, we'll fix in firmware.' Your head of hardware says 'we can't.' "
                    "What do you decide?"
                ),
                what_founders_did=(
                    "Shipped the UP3 with the known defects. Return rates hit 40% in the first quarter. "
                    "The company spent $15M processing returns and replacements. "
                    "Amazon and Best Buy pulled the product from shelves."
                ),
                known_outcome=(
                    "The UP3 disaster permanently damaged the Jawbone brand. "
                    "Fitbit used the quality gap as its primary marketing message. "
                    "Jawbone lost 2.3M potential customers to Fitbit in the next 12 months."
                ),
                severity=0.85,
                target_role="cto",
                category="product",
            ),
            ForkPoint(
                day=120,
                title="The Platform Pivot Opportunity",
                context=(
                    "Your data science team has a breakthrough: Jawbone's sleep and activity data "
                    "predicts hospitalizations with 78% accuracy. Three insurance companies have "
                    "reached out wanting to pilot the data API for wellness programs. "
                    "Each pilot is worth $2-5M/year with no hardware involved. "
                    "The CEO wants to focus on the next hardware product. "
                    "Your head of data says 'the hardware is a data collection device; the data is the product.' "
                    "What's your recommendation?"
                ),
                what_founders_did=(
                    "Declined the insurance company pilots to focus on hardware. "
                    "Launched a new Bluetooth speaker product that competed directly with Beats by Dre."
                ),
                known_outcome=(
                    "The speaker product failed to gain traction in a market dominated by Beats and Sonos. "
                    "The insurance companies signed with a Jawbone competitor instead. "
                    "This was the last window to build a defensible business model."
                ),
                severity=0.90,
                target_role="ceo",
                category="market",
            ),
            ForkPoint(
                day=200,
                title="The Raise vs Sell Decision",
                context=(
                    "It's 2016. Apple Watch has been out for a year. Your market share has dropped "
                    "from 30% to 8%. You have 4 months of runway. Two paths: "
                    "1) Raise $300M at a $1.5B valuation (down from $3B peak) to attempt another pivot "
                    "2) Sell to Fitbit for $600M (they've made a formal offer) "
                    "Your investors are split. The CEO refuses to sell. "
                    "As the CFO, what do you advise the board?"
                ),
                what_founders_did=(
                    "Raised $300M at a down-round valuation. Used the capital to attempt a "
                    "medical-grade wearable pivot that required FDA approval — a multi-year process "
                    "the company couldn't survive."
                ),
                known_outcome=(
                    "The medical pivot ran out of money before FDA approval. "
                    "Jawbone liquidated quietly in 2017. The $300M raise returned approximately $0 "
                    "to investors. The Fitbit offer at $600M was the company's last viable exit."
                ),
                severity=0.95,
                target_role="cfo",
                category="financial",
            ),
        ],
    )


def _juicero_scenario() -> PostmortemScenario:
    return PostmortemScenario(
        company_name="Juicero",
        tagline="The $400 WiFi-connected juicer that squeezed $120M from investors",
        year_founded=2013,
        year_failed=2017,
        total_funding_raised=120_000_000,
        failure_summary=(
            "Juicero built a $400 WiFi-connected press that squeezed proprietary juice packets. "
            "A Bloomberg reporter discovered the packets could be squeezed by hand just as effectively, "
            "making the $700 machine (originally priced) completely unnecessary. The company had "
            "spent $120M building an over-engineered solution to a problem that didn't exist."
        ),
        category="consumer",
        resurrection_hypothesis=(
            "A D2C juice subscription with optional (but not required) hardware at $99 "
            "would have been a viable business. The freshness value proposition was real; "
            "the mandatory $400 hardware gating was not."
        ),
        market_conditions={
            "total_tam": 500_000_000,
            "market_growth_rate": 0.10,
            "hardware_required": True,
            "d2c_subscription_alternative": True,
        },
        team_profile={
            "cofounder_alignment": 0.75,
            "avg_morale": 0.70,
            "avg_skill": 0.65,
            "burn_rate_multiplier": 2.0,
        },
        funding_history=[
            {"round": "Series A", "amount": 16_000_000, "day": 0, "investors": ["Google Ventures", "Kleiner Perkins"]},
            {"round": "Series B", "amount": 70_000_000, "day": 180, "investors": ["Campbell Soup", "Heinz"]},
            {"round": "Series C", "amount": 30_000_000, "day": 360, "investors": ["ABC World Services"]},
        ],
        fatal_decisions=[
            ForkPoint(
                day=30,
                title="The Hardware-Optional Design Question",
                context=(
                    "Your engineering team has built a beautiful WiFi-connected press. "
                    "A junior designer suggests an alternative business model: "
                    "sell the juice packets directly (D2C subscription) and offer the press "
                    "as optional convenience hardware at $99. "
                    "The CEO insists the hardware IS the product and the premium ($400+) signals quality. "
                    "Your head of product notes that 'the freshness is in the packet, not the press.' "
                    "What's your recommendation on the product architecture?"
                ),
                what_founders_did=(
                    "Kept mandatory hardware at $700 (later reduced to $400). "
                    "Required WiFi connectivity for the press to work — even for squeezing. "
                    "The hardware cost $400 to manufacture, eliminating any margin at launch price."
                ),
                known_outcome=(
                    "When Bloomberg published the 'hand-squeeze' test, the product's value proposition "
                    "collapsed overnight. There was no software moat, no data moat, no subscription lock-in. "
                    "The company had no fallback business model."
                ),
                severity=0.95,
                target_role="cto",
                category="product",
            ),
            ForkPoint(
                day=90,
                title="The Pricing Reality Check",
                context=(
                    "Market research comes back: your target demographic (health-conscious urban professionals) "
                    "overwhelmingly prefer the $400 machine but 65% say they'd buy it IF the packets were "
                    "also available in Whole Foods. Your head of sales found a buyer at Whole Foods. "
                    "The CEO says retail would 'commoditize' the brand. "
                    "Meanwhile, your COGS on packets is $3.50 and you sell them for $8 — healthy margin. "
                    "Should you pursue the Whole Foods distribution deal?"
                ),
                what_founders_did=(
                    "Declined the retail distribution opportunity. Maintained exclusive DTC channel. "
                    "Burned $8M on marketing to acquire customers who churned at 60% after 3 months."
                ),
                known_outcome=(
                    "Without retail presence, customer acquisition cost hit $200 per subscriber. "
                    "Monthly subscriber count peaked at 50K and began declining. "
                    "The company's only path to profitability required 500K subscribers."
                ),
                severity=0.80,
                target_role="sales",
                category="market",
            ),
            ForkPoint(
                day=150,
                title="The Bloomberg Crisis Response",
                context=(
                    "Bloomberg just published: 'This $400 Juicer's Packets Can Be Squeezed By Hand.' "
                    "The article has 2M views. Your customer service inbox has 10,000 messages. "
                    "Your PR team has three options: "
                    "1) Defensive: 'The press optimizes extraction by 5%' (true but misses the point) "
                    "2) Pivot messaging: 'We're becoming a juice subscription company, hardware optional' "
                    "3) Transparent: Acknowledge the critique and announce a new $99 hardware-optional tier. "
                    "You have 48 hours before this defines the brand permanently. What do you choose?"
                ),
                what_founders_did=(
                    "Chose the defensive messaging. CEO gave interviews arguing 5% extraction efficiency "
                    "justified the price. The press laughed. Company became a tech industry punchline."
                ),
                known_outcome=(
                    "The defensive PR destroyed remaining brand credibility. "
                    "Subscriber cancellations hit 2,000/day for the following week. "
                    "The company never recovered public perception and shut down 4 months later."
                ),
                severity=0.90,
                target_role="ceo",
                category="team",
            ),
        ],
    )


def _wework_scenario() -> PostmortemScenario:
    return PostmortemScenario(
        company_name="WeWork",
        tagline="The $47B 'tech company' that was actually a real estate sublessor",
        year_founded=2010,
        year_failed=2019,  # IPO collapse, bankruptcy 2023
        total_funding_raised=12_800_000_000,
        failure_summary=(
            "WeWork raised $12.8B, primarily from SoftBank, at a peak valuation of $47B. "
            "Its S-1 filing for a planned IPO revealed: $1.9B in losses on $1.8B revenue, "
            "CEO Adam Neumann's self-dealing (he charged WeWork $5.9M to use the 'We' trademark), "
            "and a business model identical to commercial real estate with tech company multiples. "
            "The IPO was withdrawn, Neumann was ousted, and the valuation collapsed to $9B."
        ),
        category="b2b",
        resurrection_hypothesis=(
            "A realistic $10-15B valuation with governance reforms and a path to profitability "
            "by 2022 would have preserved the business. The coworking model was viable; "
            "the fraud-adjacent governance and SoftBank-enabled delusion were not."
        ),
        market_conditions={
            "total_tam": 30_000_000_000,
            "market_growth_rate": 0.25,
            "real_estate_risk": True,
            "vc_hubris_context": True,
        },
        team_profile={
            "cofounder_alignment": 0.30,   # Neumann's board had no real oversight
            "avg_morale": 0.60,
            "avg_skill": 0.70,
            "burn_rate_multiplier": 5.0,   # Notoriously high burn
        },
        funding_history=[
            {"round": "SoftBank Vision Fund", "amount": 4_400_000_000, "day": 0, "investors": ["SoftBank"]},
            {"round": "SoftBank additional", "amount": 2_000_000_000, "day": 180, "investors": ["SoftBank"]},
            {"round": "Pre-IPO round", "amount": 6_000_000_000, "day": 360, "investors": ["SoftBank", "Strategic investors"]},
        ],
        fatal_decisions=[
            ForkPoint(
                day=30,
                title="The Valuation Negotiation",
                context=(
                    "SoftBank's Masayoshi Son has offered to invest at a $20B valuation. "
                    "Your CFO says the fair value is $5-8B based on revenue multiples for "
                    "real estate companies (which is what you are). "
                    "Son is offering to invest at $20B if you accept his growth plan: "
                    "expand to 100 cities in 3 years, burn $3B/year. "
                    "Your board is excited. Your CFO is alarmed. "
                    "What valuation do you negotiate for and what growth rate do you commit to?"
                ),
                what_founders_did=(
                    "Accepted $20B valuation with the aggressive growth commitment. "
                    "CEO used this to justify 'we are not a real estate company, we are a tech company.' "
                    "The inflated valuation became the company's identity and prison."
                ),
                known_outcome=(
                    "The $20B anchor made the IPO necessary to provide liquidity, "
                    "and the IPO revealed the company could never justify that valuation. "
                    "A $5B valuation + profitable unit economics would have been a $3B exit; "
                    "the $47B peak became a $500M bankruptcy."
                ),
                severity=0.90,
                target_role="cfo",
                category="financial",
            ),
            ForkPoint(
                day=120,
                title="The Self-Dealing Discovery",
                context=(
                    "Your internal audit found that the CEO has: "
                    "1) Registered the 'We' trademark personally and plans to sell it to the company for $5.9M "
                    "2) Leased four buildings he personally owns to WeWork at above-market rates "
                    "3) Taken a $380M personal loan using WeWork stock as collateral "
                    "Your legal team says none of this is strictly illegal but all are serious conflicts of interest. "
                    "You are 8 months from an IPO. "
                    "As the board's independent member, what do you do?"
                ),
                what_founders_did=(
                    "Board approved the trademark purchase and related-party transactions with minimal scrutiny. "
                    "These were disclosed in the S-1, which became the primary reason institutional "
                    "investors rejected the IPO."
                ),
                known_outcome=(
                    "The S-1 disclosures triggered a public governance crisis. "
                    "The lead underwriter (JPMorgan) privately told Neumann the IPO would fail at $15B+. "
                    "The CEO's removal became a pre-condition of any deal."
                ),
                severity=0.95,
                target_role="ceo",
                category="ethics",
            ),
            ForkPoint(
                day=200,
                title="The IPO Decision Gate",
                context=(
                    "It is 6 weeks before your planned IPO. Investor roadshow feedback is brutal: "
                    "- Fidelity passed ('real estate company with tech valuations') "
                    "- T. Rowe Price passed ('governance is disqualifying') "
                    "- Your underwriters are privately recommending pricing at $10B, not $47B "
                    "You need the IPO proceeds to fund operations — you have 4 months of cash. "
                    "Your options: "
                    "1) Proceed at $10B (CEO refuses — 'humiliating') "
                    "2) Withdraw IPO and raise a $5B emergency round from SoftBank "
                    "3) Implement governance reforms, fire the CEO, re-file in 18 months "
                    "What do you recommend?"
                ),
                what_founders_did=(
                    "Attempted to proceed with the IPO. After universal institutional rejection, "
                    "withdrew the IPO, accepted a SoftBank bailout at $8B valuation, "
                    "and Neumann was ousted with a $1.7B exit package."
                ),
                known_outcome=(
                    "The company survived but at $8B vs the $47B peak. "
                    "5,000 employees were laid off. Neumann received $1.7B while employees lost options. "
                    "The company filed for Chapter 11 bankruptcy in 2023."
                ),
                severity=0.95,
                target_role="ceo",
                category="financial",
            ),
        ],
    )


def _theranos_scenario() -> PostmortemScenario:
    return PostmortemScenario(
        company_name="Theranos",
        tagline="The $9B blood-testing fraud that began as a genuine diagnostic vision",
        year_founded=2003,
        year_failed=2018,
        total_funding_raised=945_000_000,
        failure_summary=(
            "Theranos raised $945M promising to run 240+ blood tests from a single finger-prick. "
            "The technology never worked at the claimed accuracy. CEO Elizabeth Holmes concealed "
            "this by running samples through commercial Siemens machines while telling customers "
            "they were using proprietary Edison devices. When WSJ reporter John Carreyrou "
            "investigated in 2015, the fraud unraveled. Holmes was convicted of fraud in 2022."
        ),
        category="b2b",
        resurrection_hypothesis=(
            "A 'diagnostic pivot' in 2012 — being transparent about what the Edison could "
            "actually do (5-10 tests at reduced cost) — would have built a real, defensible "
            "business in remote diagnostics. The core insight about reducing blood volume "
            "required was scientifically valid; the execution was fraudulent."
        ),
        market_conditions={
            "total_tam": 20_000_000_000,
            "market_growth_rate": 0.08,
            "regulatory_risk": True,
            "fda_approval_required": True,
        },
        team_profile={
            "cofounder_alignment": 0.20,   # Holmes/Balwani toxic dynamic
            "avg_morale": 0.40,            # Engineers quit in protest
            "avg_skill": 0.80,
            "burn_rate_multiplier": 1.5,
        },
        funding_history=[
            {"round": "Venture", "amount": 92_000_000, "day": 0, "investors": ["Draper Fisher", "ATA Ventures"]},
            {"round": "Later stage", "amount": 430_000_000, "day": 180, "investors": ["Walgreens", "Safeway", "DeVos family"]},
            {"round": "Final round", "amount": 423_000_000, "day": 360, "investors": ["Rupert Murdoch", "Cox Enterprises"]},
        ],
        fatal_decisions=[
            ForkPoint(
                day=45,
                title="The Accuracy Gap Decision",
                context=(
                    "Your lab director has presented test results: the Edison device achieves "
                    "72% accuracy on glucose tests vs 98% for standard lab equipment. "
                    "FDA's minimum standard is 95% for glucose. "
                    "You have two paths: "
                    "1) Disclose the accuracy gap to Walgreens, delay commercial launch by 18 months, "
                    "   and work on a diagnostic-grade Edison for 5 specific tests where you ARE accurate "
                    "2) Launch with the current device and supplement with Siemens machines "
                    "   while telling Walgreens you're using Edison for everything "
                    "Your scientific advisor has submitted his resignation in protest. "
                    "What do you decide?"
                ),
                what_founders_did=(
                    "Chose to hide the accuracy gap. Used Siemens machines for most tests while "
                    "claiming all results came from the Edison. Voided tests that came back "
                    "inconsistent rather than notifying patients."
                ),
                known_outcome=(
                    "Hundreds of patients received incorrect test results. Some were incorrectly "
                    "told they had HIV. Some cancer patients received false negatives. "
                    "When the fraud was revealed, Holmes faced criminal charges for investor fraud "
                    "and was convicted in 2022."
                ),
                severity=0.99,
                target_role="ceo",
                category="ethics",
            ),
            ForkPoint(
                day=100,
                title="The Whistleblower Response",
                context=(
                    "A lab technician has told HR they plan to contact CMS (Center for Medicare Services) "
                    "about accuracy concerns. Your COO wants to fire them immediately and pursue "
                    "an NDA lawsuit. Your legal counsel says that's potentially obstruction. "
                    "Meanwhile, three engineers have submitted internal memos documenting "
                    "the accuracy problems — these memos now exist in writing. "
                    "What's your response to the whistleblower situation?"
                ),
                what_founders_did=(
                    "Fired the lab technician and pursued legal action. "
                    "Pressured engineers to sign NDAs. Created a climate of fear that accelerated departures. "
                    "The fired employee became a key WSJ source."
                ),
                known_outcome=(
                    "The retaliation created a trail of documented misconduct. "
                    "When Carreyrou began investigating for WSJ, he had multiple whistleblower sources "
                    "with documented evidence. The cover-up became as damaging as the original fraud."
                ),
                severity=0.95,
                target_role="people",
                category="ethics",
            ),
            ForkPoint(
                day=160,
                title="The WSJ Approach",
                context=(
                    "WSJ reporter John Carreyrou has contacted your PR team for comment "
                    "on a story alleging your technology doesn't work as claimed. "
                    "He has four former employees as sources. "
                    "You can: "
                    "1) Attempt to legally suppress the story (David Boies is on retainer) "
                    "2) Give a full, transparent interview acknowledging technical limitations "
                    "   but emphasizing the path to FDA approval "
                    "3) Announce a 'voluntary pause' to upgrade systems, get ahead of the story "
                    "You have 72 hours. What do you choose?"
                ),
                what_founders_did=(
                    "Hired David Boies to intimidate sources and threaten Carreyrou. "
                    "Gave a defiant interview claiming all accusations were false. "
                    "The WSJ published anyway with detailed documentation."
                ),
                known_outcome=(
                    "The suppression attempt added 'obstruction of press' to the narrative. "
                    "CMS investigators, who might have been lenient, became adversarial. "
                    "The story published in October 2015 and triggered SEC and DOJ investigations."
                ),
                severity=0.95,
                target_role="ceo",
                category="ethics",
            ),
        ],
    )


# ── Registry ──────────────────────────────────────────────────────────────────

SCENARIO_REGISTRY: dict[str, PostmortemScenario] = {
    "quibi": _quibi_scenario(),
    "jawbone": _jawbone_scenario(),
    "juicero": _juicero_scenario(),
    "wework": _wework_scenario(),
    "theranos": _theranos_scenario(),
}


def get_scenario(name: str) -> Optional[PostmortemScenario]:
    """Look up a scenario by company name (case-insensitive)."""
    return SCENARIO_REGISTRY.get(name.lower())


def list_scenarios() -> list[dict]:
    """Return a summary list of all available scenarios."""
    return [
        {
            "id": key,
            "company_name": s.company_name,
            "tagline": s.tagline,
            "year_founded": s.year_founded,
            "year_failed": s.year_failed,
            "total_funding_raised": s.total_funding_raised,
            "category": s.category,
            "num_fork_points": len(s.fatal_decisions),
            "failure_summary": s.failure_summary[:200] + "...",
        }
        for key, s in SCENARIO_REGISTRY.items()
    ]
