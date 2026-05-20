"""
domains/locations/ — Geographic reference data (cities, zones, ZIPs).

Cross-domain lookup tables referenced by providers (home_city_code),
admin dashboard (city switcher), and matching (geographic constraints).

Plan 24 §3 (P-2 + A-1) introduces the `cities` table. Future expansion:
`service_zones` for intra-city polygons and `surge_rules` for
time-windowed pricing (Plan 24 §5.2 A-2/A-3).
"""
