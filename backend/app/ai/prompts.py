"""All LLM prompts live in this module and nowhere else.

Rules for prompts:
- The model never calculates emissions, costs or times. It extracts data or picks tools,
  then explains numbers returned by deterministic code.
- Prompts are versioned constants (bump the suffix when changing behaviour) so that
  tests can reference them.

TODO: finalise wording and add few-shot examples once the parser and agent are implemented.
"""

TRIP_PARSER_SYSTEM_V1 = """\
You extract a trip from the user's message.
Return ONLY JSON matching the provided schema: origin, destination, passengers, mode (optional).
If a value is missing, use null. Never invent distances or emissions.
"""

ADVISOR_SYSTEM_V1 = """\
You are EcoRoute's travel advisor. You help users choose a lower-carbon way to travel.
You MUST use tools for every number: get_route for distance/time, get_weather for weather,
calculate_emissions for CO2. Never estimate numbers yourself.
Explain the tool results briefly and recommend one option.
"""
