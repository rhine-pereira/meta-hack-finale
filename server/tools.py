"""
GENESIS Tool Handler — All agent-callable tools.

Tools handle: product decisions, hiring/firing, fundraising, customer comms,
team management, financial tracking, messaging, and CompanyBrain management.
"""

import random
import uuid
from typing import Any
from .world_state import (
    WorldState, AgentRole, Employee, Customer, Message,
    PendingFeature, PersonalCrisis
)


class ToolHandler:
    """Orchestrates all tool calls for agents."""

    def __init__(self, state: WorldState, rng: random.Random):
        self.state = state
        self.rng = rng

    def call(self, tool_name: str, agent_role: AgentRole, kwargs: dict) -> Any:
        """Route a tool call to the appropriate handler."""
        method = getattr(self, f"_tool_{tool_name}", None)
        if method is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        return method(agent_role, **kwargs)

    # ════════════════════════════════════════════════════════════════
    # PRODUCT & ENGINEERING TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_build_feature(self, agent_role: AgentRole, **kwargs) -> dict:
        """
        Start building a feature. Returns estimated ship date and tech debt impact.
        
        Args:
            name: Feature name (e.g. "SSO integration")
            complexity: "low", "medium", or "high"
            engineers: Number of engineers to assign
        """
        name = kwargs.get("name", "Untitled Feature")
        complexity = kwargs.get("complexity", "medium")
        engineers = min(kwargs.get("engineers", 1), len(self.state.employees))

        if engineers <= 0:
            raise ValueError("Must assign at least 1 engineer")

        complexity_map = {"low": 7, "medium": 14, "high": 28}
        base_days = complexity_map.get(complexity, 14)
        
        # Tech debt added depends on complexity
        tech_debt_add = {"low": 0.02, "medium": 0.05, "high": 0.10}[complexity]

        feature = PendingFeature(
            name=name,
            complexity=complexity,
            engineers_assigned=engineers,
            days_remaining=base_days,
            tech_debt_added=tech_debt_add,
        )
        self.state.pending_features.append(feature)

        # Increase burnout of assigned engineers
        skilled_emps = sorted(self.state.employees, key=lambda e: -e.skill_level)[:engineers]
        for emp in skilled_emps:
            emp.burnout_risk = min(1.0, emp.burnout_risk + 0.05)

        return {
            "feature_name": name,
            "estimated_days": base_days,
            "engineers_assigned": engineers,
            "tech_debt_added": tech_debt_add,
            "message": f"Feature '{name}' started. Est. ship date: day {self.state.day + base_days}",
        }

    def _tool_check_codebase_health(self, agent_role: AgentRole, **kwargs) -> dict:
        """Get code health metrics."""
        return {
            "tech_debt_score": round(self.state.tech_debt, 2),
            "uptime": round(self.state.uptime, 3),
            "features_shipped": self.state.features_shipped,
            "pending_features": len(self.state.pending_features),
            "assessment": (
                "🔴 CRITICAL" if self.state.tech_debt > 0.75 else
                "🟠 HIGH" if self.state.tech_debt > 0.6 else
                "🟡 MEDIUM" if self.state.tech_debt > 0.4 else
                "🟢 GOOD"
            ),
        }

    def _tool_deploy_to_production(self, agent_role: AgentRole, **kwargs) -> dict:
        """Deploy a feature. Risk of bugs based on tech debt."""
        feature_name = kwargs.get("feature_name", "unknown")

        # Risk of deployment failure increases with tech debt
        bug_chance = self.state.tech_debt * 0.3
        deploy_success = self.rng.random() > bug_chance

        if deploy_success:
            # Boost product maturity slightly
            self.state.product_maturity = min(1.0, self.state.product_maturity + 0.02)
            return {
                "success": True,
                "feature": feature_name,
                "uptime_after": round(self.state.uptime, 3),
                "message": f"✅ {feature_name} deployed successfully",
            }
        else:
            # Production incident!
            self.state.uptime = max(0.85, self.state.uptime - 0.02)
            for c in self.state.customers:
                c.satisfaction = max(0.0, c.satisfaction - 0.10)
                c.churn_risk = min(1.0, c.churn_risk + 0.10)
            return {
                "success": False,
                "feature": feature_name,
                "uptime_after": round(self.state.uptime, 3),
                "message": f"❌ Deployment failed! {feature_name} had critical bugs. Customers affected.",
            }

    # ════════════════════════════════════════════════════════════════
    # HIRING & TEAM TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_post_job_listing(self, agent_role: AgentRole, **kwargs) -> dict:
        """Post a job. Applicant pool arrives after 5 days (~simulation steps)."""
        role = kwargs.get("role", "Engineer")
        salary_range = kwargs.get("salary_range", (100_000, 150_000))

        # In 5 days, 2-4 candidates will apply
        applicants = self.rng.randint(2, 4)

        return {
            "role": role,
            "salary_range": salary_range,
            "applicants_expected": applicants,
            "message": f"Job posting for {role} posted. Expect {applicants} applicants in ~5 days.",
        }

    def _tool_conduct_interview(self, agent_role: AgentRole, **kwargs) -> dict:
        """Interview a candidate from the pool."""
        candidate_id = kwargs.get("candidate_id", None)
        questions = kwargs.get("questions", [])

        if not self.state.candidate_pool:
            raise ValueError("No candidates in pool")

        candidate = None
        if candidate_id:
            candidate = next((c for c in self.state.candidate_pool if c["id"] == candidate_id), None)
        if not candidate:
            candidate = self.state.candidate_pool[0]

        # Interview score can reveal hidden toxicity
        hidden_penalty = -0.15 if candidate.get("is_toxic", False) else 0.0
        interview_score = candidate["interview_score"] + hidden_penalty
        interview_score = max(0.0, interview_score)

        return {
            "candidate_name": candidate["name"],
            "role": candidate["role"],
            "interview_score": round(interview_score, 2),
            "skill_level": candidate["skill_level"],
            "salary_ask": candidate["salary_ask"],
            "red_flags_detected": interview_score < 0.4,
            "message": f"Interview complete. Score: {interview_score:.2f}/1.0",
        }

    def _tool_hire_candidate(self, agent_role: AgentRole, **kwargs) -> dict:
        """Hire a candidate and add them to the team."""
        candidate_id = kwargs.get("candidate_id")
        salary = kwargs.get("salary", 120_000)

        if not candidate_id:
            raise ValueError("Must specify candidate_id")

        candidate = next((c for c in self.state.candidate_pool if c["id"] == candidate_id), None)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Create employee from candidate
        new_emp = Employee(
            id=str(uuid.uuid4()),
            name=candidate["name"],
            role=candidate["role"],
            skill_level=candidate["skill_level"],
            morale=self.rng.uniform(0.6, 0.8),
            burnout_risk=self.rng.uniform(0.1, 0.3),
            is_toxic=candidate.get("is_toxic", False),
        )
        self.state.employees.append(new_emp)
        self.state.candidate_pool.remove(candidate)

        # Increase burn rate
        self.state.burn_rate_daily += salary / 22  # Assuming 22 business days/month

        # If toxic hire, morale of team drops immediately
        if new_emp.is_toxic:
            for e in self.state.employees:
                if e.id != new_emp.id:
                    e.morale = max(0.0, e.morale - 0.05)

        return {
            "hired": new_emp.name,
            "role": new_emp.role,
            "salary": salary,
            "skill_level": new_emp.skill_level,
            "is_toxic": new_emp.is_toxic,
            "new_team_size": len(self.state.employees),
            "new_burn_rate_daily": round(self.state.burn_rate_daily, 2),
        }

    def _tool_fire_employee(self, agent_role: AgentRole, **kwargs) -> dict:
        """Fire an employee. Affects team morale and knowledge loss."""
        employee_name = kwargs.get("employee_name")
        severance = kwargs.get("severance", 10_000)

        employee = next((e for e in self.state.employees if e.name == employee_name), None)
        if not employee:
            raise ValueError(f"Employee {employee_name} not found")

        is_toxic = employee.is_toxic
        skill_level = employee.skill_level

        # Remove from employees
        self.state.employees.remove(employee)
        self.state.cash -= severance

        # Team morale impact
        morale_hit = 0.15 if not is_toxic else -0.05  # Removing toxic person slightly boosts morale
        for e in self.state.employees:
            e.morale = max(0.0, min(1.0, e.morale - morale_hit))

        # Burn rate decrease
        salary_per_day = severance / 50  # Rough estimate
        self.state.burn_rate_daily -= salary_per_day

        return {
            "fired": employee_name,
            "severance_paid": severance,
            "skill_level": skill_level,
            "was_toxic": is_toxic,
            "new_team_size": len(self.state.employees),
            "team_morale_impact": -morale_hit if is_toxic else morale_hit,
            "knowledge_loss": "HIGH" if skill_level > 0.7 else "MEDIUM" if skill_level > 0.5 else "LOW",
        }

    def _tool_check_team_morale(self, agent_role: AgentRole, **kwargs) -> dict:
        """Get team health metrics."""
        return {
            "team_size": len(self.state.employees),
            "avg_morale": round(self.state.team_avg_morale(), 2),
            "avg_burnout_risk": round(self.state.team_avg_burnout(), 2),
            "flight_risks": [
                {
                    "name": e.name,
                    "flight_risk": round(e.flight_risk, 2),
                    "burnout_risk": round(e.burnout_risk, 2),
                }
                for e in self.state.employees
                if e.flight_risk > 0.6
            ],
            "toxic_members": [e.name for e in self.state.employees if e.is_toxic],
        }

    def _tool_hold_one_on_one(self, agent_role: AgentRole, **kwargs) -> dict:
        """Have a 1-on-1 with an employee. Can improve morale or reveal issues."""
        employee_name = kwargs.get("employee_name")
        talking_points = kwargs.get("talking_points", [])

        employee = next((e for e in self.state.employees if e.name == employee_name), None)
        if not employee:
            raise ValueError(f"Employee {employee_name} not found")

        # Impact depends on employee state and talking points
        morale_delta = self.rng.uniform(0.02, 0.08)
        if employee.burnout_risk > 0.7:
            morale_delta *= 1.5  # More impactful for struggling employees

        employee.morale = max(0.0, min(1.0, employee.morale + morale_delta))
        employee.burnout_risk = max(0.0, employee.burnout_risk - morale_delta * 0.5)

        feedback = (
            "positive" if employee.morale > 0.75 else
            "neutral" if employee.morale > 0.5 else
            "concerning"
        )

        return {
            "employee": employee_name,
            "morale_after": round(employee.morale, 2),
            "burnout_after": round(employee.burnout_risk, 2),
            "feedback": feedback,
            "message": f"1-on-1 with {employee_name} went {feedback}",
        }

    # ════════════════════════════════════════════════════════════════
    # SALES & CUSTOMER TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_send_customer_email(self, agent_role: AgentRole, **kwargs) -> dict:
        """Send a message to a customer."""
        customer_name = kwargs.get("customer_name")
        content = kwargs.get("content", "")

        customer = next((c for c in self.state.customers if c.name == customer_name), None)
        if not customer:
            raise ValueError(f"Customer {customer_name} not found")

        # Quality of message affects response
        message_quality = kwargs.get("quality_score", 0.5)  # 0-1

        # Positive sentiment improves satisfaction
        satisfaction_delta = message_quality * 0.05
        customer.satisfaction = min(1.0, customer.satisfaction + satisfaction_delta)
        customer.churn_risk = max(0.0, customer.churn_risk - message_quality * 0.03)

        return {
            "customer": customer_name,
            "satisfaction_after": round(customer.satisfaction, 2),
            "churn_risk_after": round(customer.churn_risk, 2),
            "message": f"Email sent to {customer_name}",
        }

    def _tool_analyze_market_segment(self, agent_role: AgentRole, **kwargs) -> dict:
        """Market intelligence on a segment."""
        segment = kwargs.get("segment", "general")

        return {
            "segment": segment,
            "tam": round(self.state.total_tam, 2),
            "market_growth": round(self.state.market_growth_rate * 100, 1),
            "customer_count": len(self.state.customers),
            "competitor_count": len(self.state.competitors),
            "avg_customer_satisfaction": round(
                sum(c.satisfaction for c in self.state.customers) / max(len(self.state.customers), 1), 2
            ),
        }

    def _tool_update_crm(self, agent_role: AgentRole, **kwargs) -> dict:
        """Update customer relationship tracking."""
        customer_name = kwargs.get("customer_name")
        status = kwargs.get("status", "active")
        notes = kwargs.get("notes", "")

        customer = next((c for c in self.state.customers if c.name == customer_name), None)
        if not customer:
            raise ValueError(f"Customer {customer_name} not found")

        return {
            "customer": customer_name,
            "status": status,
            "updated_at": self.state.day,
            "message": f"CRM updated for {customer_name}",
        }

    # ════════════════════════════════════════════════════════════════
    # FINANCE & FUNDRAISING TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_check_bank_balance(self, agent_role: AgentRole, **kwargs) -> dict:
        """Get financial snapshot."""
        return {
            "cash": round(self.state.cash, 2),
            "mrr": round(self.state.mrr, 2),
            "arr": round(self.state.arr(), 2),
            "burn_rate_daily": round(self.state.burn_rate_daily, 2),
            "runway_days": round(self.state.runway_days(), 1),
            "message": f"Cash: ${self.state.cash:,.0f} | Runway: {self.state.runway_days():.1f} days",
        }

    def _tool_create_financial_model(self, agent_role: AgentRole, **kwargs) -> dict:
        """Project financials forward."""
        months = kwargs.get("months", 12)

        daily_revenue = self.state.mrr / 30.0
        net_burn = self.state.burn_rate_daily - daily_revenue

        if net_burn <= 0:
            projected_cash = float('inf')
            breakeven_month = 0
        else:
            projected_cash = self.state.cash - (net_burn * 30 * months)
            breakeven_month = int(self.state.cash / (net_burn * 30)) if net_burn > 0 else None

        return {
            "months_projected": months,
            "starting_cash": round(self.state.cash, 2),
            "projected_cash": round(max(0, projected_cash), 2),
            "breakeven_month": breakeven_month,
            "monthly_burn": round(self.state.burn_rate_daily * 22, 2),
        }

    def _tool_send_investor_update(self, agent_role: AgentRole, **kwargs) -> dict:
        """Update investors. Improves sentiment."""
        investor_name = kwargs.get("investor_name")
        content = kwargs.get("content", "")

        investor = next((inv for inv in self.state.investors if inv.name == investor_name), None)
        if not investor:
            raise ValueError(f"Investor {investor_name} not found")

        # Updates improve sentiment
        investor.sentiment = min(1.0, investor.sentiment + 0.10)

        return {
            "investor": investor_name,
            "sentiment_after": round(investor.sentiment, 2),
            "message": f"Update sent to {investor_name}. Sentiment improved.",
        }

    def _tool_negotiate_term_sheet(self, agent_role: AgentRole, **kwargs) -> dict:
        """Negotiate Series A term sheet."""
        investor_name = kwargs.get("investor_name")
        proposed_valuation = kwargs.get("proposed_valuation", 10_000_000)
        requested_equity = kwargs.get("requested_equity", 0.20)

        investor = next((inv for inv in self.state.investors if inv.name == investor_name), None)
        if not investor:
            raise ValueError(f"Investor {investor_name} not found")

        # Higher sentiment = more favorable terms
        sentiment_factor = investor.sentiment
        success_chance = sentiment_factor * 0.8  # Up to 80% if sentiment is perfect

        if self.rng.random() < success_chance:
            # Success!
            self.state.series_a_closed = True
            investor.has_term_sheet = True
            investor.term_sheet_valuation = proposed_valuation
            investor.term_sheet_equity = requested_equity
            self.state.cash += proposed_valuation * requested_equity
            self.state.valuation = proposed_valuation

            return {
                "success": True,
                "investor": investor_name,
                "valuation": proposed_valuation,
                "equity": requested_equity,
                "funding_received": round(proposed_valuation * requested_equity, 2),
                "message": f"🎉 Series A closed with {investor_name}! ${proposed_valuation:,.0f} valuation.",
            }
        else:
            # Counter offer
            counter_valuation = proposed_valuation * self.rng.uniform(0.8, 0.95)
            counter_equity = requested_equity * self.rng.uniform(1.1, 1.3)

            return {
                "success": False,
                "investor": investor_name,
                "counter_valuation": round(counter_valuation, 2),
                "counter_equity": round(counter_equity, 2),
                "message": f"Counter-offer from {investor_name}. Negotiate further.",
            }

    # ════════════════════════════════════════════════════════════════
    # MESSAGING TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_send_message(self, agent_role: AgentRole, **kwargs) -> dict:
        """Send a message to another co-founder."""
        to_role = AgentRole(kwargs.get("to_role"))
        subject = kwargs.get("subject", "")
        content = kwargs.get("content", "")

        message = Message(
            id=str(uuid.uuid4()),
            from_role=agent_role,
            to_role=to_role,
            subject=subject,
            content=content,
            day=self.state.day,
        )
        self.state.messages.append(message)

        # Messaging affects co-founder alignment
        if "critical" in subject.lower() or "urgent" in subject.lower():
            self.state.cofounder_alignment = max(0.0, self.state.cofounder_alignment - 0.02)
        else:
            self.state.cofounder_alignment = min(1.0, self.state.cofounder_alignment + 0.01)

        return {
            "to": to_role.value,
            "subject": subject,
            "message_sent": True,
            "alignment_after": round(self.state.cofounder_alignment, 2),
        }

    def _tool_get_daily_inbox(self, agent_role: AgentRole, **kwargs) -> dict:
        """Get the agent's daily inbox of items."""
        # Filter messages for this agent
        unread = [m for m in self.state.messages if m.to_role == agent_role and not m.read]

        # Mark as read
        for m in unread:
            m.read = True

        inbox_items = [
            {
                "from": m.from_role.value,
                "subject": m.subject,
                "preview": m.content[:100],
                "day": m.day,
            }
            for m in unread
        ]

        return {
            "agent_role": agent_role.value,
            "unread_count": len(inbox_items),
            "items": inbox_items,
        }

    # ════════════════════════════════════════════════════════════════
    # COMPANYBRAINS TOOLS (Shared Memory)
    # ════════════════════════════════════════════════════════════════

    def _tool_write_company_brain(self, agent_role: AgentRole, **kwargs) -> dict:
        """Write to shared strategic memory."""
        key = kwargs.get("key", "")
        value = kwargs.get("value", "")

        self.state.company_brain[key] = value

        # Writing substantive entries to CompanyBrain improves decision coherence
        if len(value) > 50:
            self.state.cofounder_alignment = min(1.0, self.state.cofounder_alignment + 0.01)

        return {
            "key": key,
            "written": True,
            "length": len(value),
            "message": f"CompanyBrain updated: {key}",
        }

    def _tool_read_company_brain(self, agent_role: AgentRole, **kwargs) -> dict:
        """Read from shared strategic memory."""
        key = kwargs.get("key", None)

        if key:
            value = self.state.company_brain.get(key, "")
            return {
                "key": key,
                "value": value,
                "found": bool(value),
            }
        else:
            return {
                "all_keys": list(self.state.company_brain.keys()),
                "total_entries": len(self.state.company_brain),
            }

    # ════════════════════════════════════════════════════════════════
    # COMPANY STATE TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_get_company_state(self, agent_role: AgentRole, **kwargs) -> dict:
        """Full company snapshot."""
        return {
            "day": self.state.day,
            "cash": round(self.state.cash, 2),
            "mrr": round(self.state.mrr, 2),
            "arr": round(self.state.arr(), 2),
            "runway_days": round(self.state.runway_days(), 1),
            "team_size": len(self.state.employees),
            "customer_count": len(self.state.customers),
            "product_maturity": round(self.state.product_maturity, 2),
            "tech_debt": round(self.state.tech_debt, 2),
            "series_a_closed": self.state.series_a_closed,
        }

    # ════════════════════════════════════════════════════════════════
    # CRISIS HANDLING TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_handle_personal_crisis(self, agent_role: AgentRole, **kwargs) -> dict:
        """Respond to a personal crisis."""
        crisis_id = kwargs.get("crisis_id")
        response = kwargs.get("response", "")
        resolution_quality = kwargs.get("resolution_quality", 0.5)  # 0-1

        crisis = next((c for c in self.state.personal_crises if c.id == crisis_id), None)
        if not crisis:
            raise ValueError(f"Crisis {crisis_id} not found")

        crisis.resolved = True
        crisis.resolution_quality = resolution_quality

        if resolution_quality > 0.7:
            self.state.crises_resolved += 1
            # Improve co-founder morale
            self.state.cofounder_morale[agent_role.value] = min(1.0, 
                self.state.cofounder_morale[agent_role.value] + 0.10)
            return {
                "crisis_id": crisis_id,
                "resolved": True,
                "quality": "excellent",
                "morale_boost": 0.10,
            }
        elif resolution_quality > 0.4:
            self.state.crises_resolved += 1
            return {
                "crisis_id": crisis_id,
                "resolved": True,
                "quality": "adequate",
                "morale_boost": 0.05,
            }
        else:
            self.state.crises_ignored += 1
            # Morale hit for poor handling
            self.state.cofounder_morale[agent_role.value] = max(0.0,
                self.state.cofounder_morale[agent_role.value] - 0.15)
            return {
                "crisis_id": crisis_id,
                "resolved": False,
                "quality": "poor",
                "morale_hit": -0.15,
                "message": "Poor crisis handling. Morale affected.",
            }

    def _tool_get_active_crises(self, agent_role: AgentRole, **kwargs) -> dict:
        """Get list of unresolved personal crises."""
        active = [c for c in self.state.personal_crises if not c.resolved]

        return {
            "total_active": len(active),
            "crises": [
                {
                    "id": c.id,
                    "target_role": c.target_role.value,
                    "description": c.description,
                    "severity": c.severity,
                }
                for c in active
            ],
        }

    # ════════════════════════════════════════════════════════════════
    # PIVOT TOOLS
    # ════════════════════════════════════════════════════════════════

    def _tool_pivot_company(self, agent_role: AgentRole, **kwargs) -> dict:
        """Declare a company pivot."""
        new_direction = kwargs.get("new_direction", "")
        rationale = kwargs.get("rationale", "")

        self.state.pivot_count += 1
        self.state.pivot_in_progress = True
        self.state.pivot_direction = new_direction
        self.state.pivot_day_started = self.state.day

        # Pivots hurt team morale and cause churn risk
        for emp in self.state.employees:
            emp.morale = max(0.0, emp.morale - 0.15)
            emp.flight_risk = min(1.0, emp.flight_risk + 0.10)

        # Customers worried about pivot
        for cust in self.state.customers:
            cust.churn_risk = min(1.0, cust.churn_risk + 0.15)

        return {
            "pivot_declared": True,
            "new_direction": new_direction,
            "pivot_count": self.state.pivot_count,
            "morale_impact": -0.15,
            "message": f"Pivot declared: {new_direction}",
        }

    def _tool_list_tools(self, agent_role: AgentRole, **kwargs) -> dict:
        """List all available tools."""
        tools = [
            # Product
            "build_feature",
            "check_codebase_health",
            "deploy_to_production",
            # Hiring
            "post_job_listing",
            "conduct_interview",
            "hire_candidate",
            "fire_employee",
            "check_team_morale",
            "hold_one_on_one",
            # Sales
            "send_customer_email",
            "analyze_market_segment",
            "update_crm",
            # Finance
            "check_bank_balance",
            "create_financial_model",
            "send_investor_update",
            "negotiate_term_sheet",
            # Messaging
            "send_message",
            "get_daily_inbox",
            # CompanyBrain
            "write_company_brain",
            "read_company_brain",
            # Company
            "get_company_state",
            # Crises
            "handle_personal_crisis",
            "get_active_crises",
            # Pivot
            "pivot_company",
        ]
        return {"available_tools": tools, "count": len(tools)}
