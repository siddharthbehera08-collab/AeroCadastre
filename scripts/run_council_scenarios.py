"""
Demonstration script for AI Council Multi-Agent Adjudication across 7 canonical scenarios.
"""
import sys
sys.path.insert(0, '.')
from backend.council.agents import evaluate_parcel_with_council
import json

scenarios = [
    {
        'name': '1. Strong building + road agreement (Routine Accept)',
        'parcel': {'id': 'SCENARIO_1', 'visible_edges': 4, 'boundary_prob_mean': 0.94, 'bldg_prob_mean': 0.92, 'compactness': 0.88, 'area_sqm': 450.0, 'road_access': True},
        'topo': 'VALID', 'conflict': 'NONE', 'anomaly': 'NONE', 'anomalies': [], 'changes': []
    },
    {
        'name': '2. Conflicting GIS evidence (Road Encroachment)',
        'parcel': {'id': 'SCENARIO_2', 'visible_edges': 3, 'boundary_prob_mean': 0.80, 'bldg_prob_mean': 0.85, 'compactness': 0.75, 'area_sqm': 320.0, 'road_access': True},
        'topo': 'VALID', 'conflict': 'ROAD_ENCROACHMENT', 'anomaly': 'NONE', 'anomalies': [{'rule_id': 'ROAD_CROSSING', 'explanation': 'Crosses road reserve corridor'}], 'changes': []
    },
    {
        'name': '3. Poor image quality & weak visual evidence',
        'parcel': {'id': 'SCENARIO_3', 'visible_edges': 1, 'boundary_prob_mean': 0.35, 'bldg_prob_mean': 0.40, 'compactness': 0.65, 'area_sqm': 500.0, 'road_access': True},
        'topo': 'VALID', 'conflict': 'NONE', 'anomaly': 'NONE', 'anomalies': [], 'changes': []
    },
    {
        'name': '4. Topology error (Self-intersection)',
        'parcel': {'id': 'SCENARIO_4', 'visible_edges': 4, 'boundary_prob_mean': 0.90, 'bldg_prob_mean': 0.88, 'compactness': 0.40, 'area_sqm': 200.0, 'road_access': True},
        'topo': 'SELF_INTERSECTION', 'conflict': 'NONE', 'anomaly': 'NONE', 'anomalies': [], 'changes': []
    },
    {
        'name': '5. Anomalous parcel (Morphology outlier / Isolation Forest)',
        'parcel': {'id': 'SCENARIO_5', 'visible_edges': 2, 'boundary_prob_mean': 0.65, 'bldg_prob_mean': 0.70, 'compactness': 0.20, 'area_sqm': 15.0, 'road_access': False},
        'topo': 'VALID', 'conflict': 'NONE', 'anomaly': 'SLIVER_POLYGON', 'anomalies': [{'rule_id': 'ANOMALY_SLIVER', 'explanation': 'Extreme aspect ratio sliver'}], 'changes': []
    },
    {
        'name': '6. Model disagreement between neural heads',
        'parcel': {'id': 'SCENARIO_6', 'visible_edges': 3, 'boundary_prob_mean': 0.75, 'bldg_prob_mean': 0.80, 'lu_prob_mean': 0.45, 'model_disagreement': 0.25, 'compactness': 0.70, 'area_sqm': 400.0, 'road_access': True},
        'topo': 'VALID', 'conflict': 'NONE', 'anomaly': 'NONE', 'anomalies': [], 'changes': []
    },
    {
        'name': '7. Field verification required (Temporal change detected)',
        'parcel': {'id': 'SCENARIO_7', 'visible_edges': 3, 'boundary_prob_mean': 0.82, 'bldg_prob_mean': 0.85, 'compactness': 0.78, 'area_sqm': 550.0, 'road_access': True},
        'topo': 'VALID', 'conflict': 'NONE', 'anomaly': 'NONE', 'anomalies': [], 'changes': [{'summary': 'New plinth construction detected between T0 and T2'}]
    }
]

def run_scenarios():
    print('='*75)
    print('AI COUNCIL MULTI-AGENT ADJUDICATION ACROSS 7 CANONICAL SCENARIOS')
    print('='*75)
    for s in scenarios:
        res = evaluate_parcel_with_council(
            parcel=s['parcel'],
            topology_status=s['topo'],
            conflict_status=s['conflict'],
            anomaly_status=s['anomaly'],
            parcel_anomalies=s['anomalies'],
            parcel_changes=s['changes']
        )
        print(s['name'])
        print(f"  Decision: {res['decision']} | Field Priority: {res['field_need']} | Confidence: {res['confidence']:.3f} ({res['confidence_category']})")
        print(f"  Agent Breakdown: Vision={res['vision_score']:.2f}, Geom={res['geometry_score']:.2f}, GIS={res['gis_score']:.2f}, ML={res['ml_score']:.2f}, AnomalyRisk={res['anomaly_score']:.2f}")
        print(f"  Key Reasons: {res['priority_reasons']}")
        print('-'*75)

if __name__ == '__main__':
    run_scenarios()
