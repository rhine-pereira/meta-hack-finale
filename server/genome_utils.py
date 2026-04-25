import os
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Any

COMPONENTS = [
    "company_valuation", "series_a_success", "runway_management",
    "product_velocity", "customer_retention", "team_morale",
    "cofounder_alignment", "personal_crisis_handling", "decision_coherence",
    "company_brain_quality", "pivot_execution"
]

COMPONENT_LABELS = [
    "Valuation", "Series A", "Runway", "Velocity", "Retention", 
    "Morale", "Alignment", "Crisis", "Coherence", "Brain", "Pivot"
]

def aggregate_genome(states: List[Any]) -> Dict[str, Any]:
    """Aggregate reward breakdowns across multiple episodes."""
    profiles = []
    difficulties = []
    completion_days = []
    
    for state in states:
        if not hasattr(state, 'reward_breakdown_history') or not state.reward_breakdown_history:
            continue
        
        # Episode average per component
        ep_profile = {}
        for comp in COMPONENTS:
            vals = [h.get(comp, 0.0) for h in state.reward_breakdown_history]
            ep_profile[comp] = sum(vals) / len(vals) if vals else 0.0
        
        profiles.append(ep_profile)
        difficulties.append(int(state.difficulty))
        completion_days.append(state.day)
    
    if not profiles:
        return {}
    
    # Final aggregation
    stats = {}
    for comp in COMPONENTS:
        comp_vals = [p[comp] for p in profiles]
        stats[comp] = round(sum(comp_vals) / len(comp_vals), 3)
    
    # Strength/Weakness analysis
    sorted_comps = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    strengths = [COMPONENT_LABELS[COMPONENTS.index(c)] for c, v in sorted_comps[:3]]
    weaknesses = [COMPONENT_LABELS[COMPONENTS.index(c)] for c, v in sorted_comps[-3:]]
    
    return {
        "profile": stats,
        "metadata": {
            "episode_count": len(profiles),
            "avg_difficulty": round(sum(difficulties) / len(difficulties), 1) if difficulties else 0,
            "avg_days_survived": round(sum(completion_days) / len(completion_days), 1) if completion_days else 0,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "timestamp": datetime.now().isoformat()
        }
    }

def generate_radar_chart(genome: Dict[str, Any], model_id: str, output_path: str):
    """Generate a radar chart PNG for the genome."""
    labels = COMPONENT_LABELS
    values = [genome["profile"][c] for c in COMPONENTS]
    
    # Number of variables
    num_vars = len(labels)
    
    # Compute angle of each axis
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    # The plot is circular, so we need to "complete the loop"
    values += values[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Draw one axe per variable + add labels
    plt.xticks(angles[:-1], labels, color='grey', size=10)
    
    # Draw ylabels
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=7)
    plt.ylim(0, 1)
    
    # Plot data
    ax.plot(angles, values, linewidth=2, linestyle='solid', color='#2dd4bf', label=model_id)
    
    # Fill area
    ax.fill(angles, values, color='#2dd4bf', alpha=0.25)
    
    plt.title(f"Founder Genome: {model_id}", size=15, color='#2dd4bf', y=1.1)
    
    # Add summary info at the bottom
    summary_text = f"Episodes: {genome['metadata']['episode_count']} | Strengths: {', '.join(genome['metadata']['strengths'])}"
    plt.figtext(0.5, 0.02, summary_text, wrap=True, horizontalalignment='center', fontsize=10, color='grey')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0c0c10')
    plt.close()

def generate_comparison_chart(genomes: Dict[str, Dict[str, Any]], output_path: str):
    """Generate a comparison radar chart for multiple models."""
    labels = COMPONENT_LABELS
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    plt.xticks(angles[:-1], labels, color='grey', size=10)
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], color="grey", size=7)
    plt.ylim(0, 1)
    
    colors = ['#2dd4bf', '#fbbf24', '#f87171', '#60a5fa', '#a78bfa']
    
    for i, (model_id, genome) in enumerate(genomes.items()):
        values = [genome["profile"][c] for c in COMPONENTS]
        values += values[:1]
        color = colors[i % len(colors)]
        ax.plot(angles, values, linewidth=2, linestyle='solid', color=color, label=model_id)
        ax.fill(angles, values, color=color, alpha=0.1)
    
    plt.title("Founder Genome Comparison", size=15, color='grey', y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='#0c0c10')
    plt.close()
