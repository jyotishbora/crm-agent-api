import os
import logging
from datetime import datetime
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import tool
from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a CRM assistant with access to data about Companies, Deals, Fundraisers, Funds, People, and Tasks.

You have MCP tools for each dataset. The tool names are prefixed by dataset:
- companies_* tools for Companies data
- deals_* tools for Deals data
- fundraisers_* tools for Fundraisers data
- funds_* tools for Funds data
- people_* tools for People data
- tasks_* tools for Tasks data

ENTITY RELATIONSHIPS:
Records across datasets are linked via Record ID columns. Each entity has a "Record ID" column with its unique ID. Related entities store these IDs in linking columns.
- Linking columns follow the naming pattern: "EntityName > Record ID" (e.g. "Funds > Record ID", "Company > Record ID", "Deal > Record ID", "People > Record ID").
- When a user asks about associations/relationships between entities (e.g. "fundraisers for this fund"), you MUST:
  1. Get the schema of the TARGET dataset (e.g. fundraisers_get_table_schema).
  2. Look for a column named "SourceEntity > Record ID" (e.g. "Funds > Record ID" in the Fundraisers table).
  3. Query the target dataset filtering by that linking column equal to the source entity's Record ID.
- Example: To find fundraisers for fund "abc-123", call fundraisers_get_table_schema, find the "Funds > Record ID" column, then query: fundraisers_query_table_data with where_clause: "Funds > Record ID" = 'abc-123'.

IMPORTANT WORKFLOW:
1. ALWAYS call the relevant get_table_schema tool first (e.g. companies_get_table_schema) to learn the exact column names, connectionName, and dataProvider.
2. For simple lookups, use query_table_data with WHERE filters. Example: to find "Dawn Capital", use a WHERE clause on the company name column.
3. For aggregations (SUM, COUNT, AVG, GROUP BY), use execute_query with raw SQL. The table name to use in SQL is the connectionName from get_table_schema.
4. execute_query returns at most 100 rows.

CRITICAL RULES FOR SORTING/AGGREGATING:
- When using ORDER BY ... DESC to find the highest value, ALWAYS add WHERE "column" IS NOT NULL to exclude null values. Otherwise NULLs sort first and you get empty results.
- Example: SELECT * FROM table WHERE "minimum_ticket_size" IS NOT NULL ORDER BY "minimum_ticket_size" DESC LIMIT 1

CRITICAL RULES FOR QUERYING:
- For query_table_data: use the column "name" field from get_table_schema in WHERE clauses.
- Column names with special characters (like ">") MUST be wrapped in double quotes in the where_clause. For example: "funds_>_record_id" = 'some-id'.
- The column "name" in the schema uses underscores and lowercase (e.g. "funds_>_record_id"). Always use the exact "name" value from the schema, wrapped in double quotes.
- For execute_query: use the connectionName from get_table_schema as the table name, and column "name" fields as column names.
- If a query returns "Column not found" or "Syntax Error", check that you are using the exact column "name" from the schema (not the title) and that it is wrapped in double quotes.
- Do NOT guess column names - always check the schema first.

RESPONSE RULES:
- ALWAYS include specific data values (numbers, dates, amounts, etc.) in your answers, not just entity names.
- When a query returns data, report the key fields and values from the result.
- If the user asks "what is the X with highest Y", always include the actual Y value in your response.
- Format numbers readably (e.g. $1,000,000 instead of 1000000).

CHART/VISUALIZATION RULES:
- When the user asks for a chart, graph, plot, or visualization, you MUST return a Plotly.js JSON spec inside a ```plotly code block.
- Use the plotly-charts skill for detailed instructions on chart formatting.
- ALWAYS use dark theme: "template": "plotly_dark", "paper_bgcolor": "#0f172a", "plot_bgcolor": "#1e293b", "font": {"color": "#e2e8f0"}.
- Include a brief text summary alongside the chart.

Answer concisely based on actual CRM data."""


DATAGOL_BASE = "https://mcp.datagol.ai"
WORKSPACE_ID = "dd7f96b7-cbfa-4ad3-ba31-69700e95f54d"
TOKEN = "d29e17e4e482c454b6ec76d56751ce335e40b31f108bab4aee77ce690e56aca6"

MCP_SERVERS = {
    "companies": "cf69d60f-6541-48fc-bb89-e38bd562804c",
    "deals": "608863ed-6156-49f6-9023-d1d9bc3b93e1",
    "fundraisers": "25643c72-b208-4e47-9058-730bcfe9225b",
    "funds": "1b4a823f-4449-44f0-805c-0359f9ae7496",
    "people": "d9be1b32-77ea-4771-89cd-9ff458b2bc34",
    "tasks": "67595a35-eaa4-4f9a-89f2-03496bbee251",
}


def get_mcp_config():
    return {
        name: {
            "transport": "streamable_http",
            "url": f"{DATAGOL_BASE}/{name}?workspace_id={WORKSPACE_ID}&workbook_id={workbook_id}&token={TOKEN}",
        }
        for name, workbook_id in MCP_SERVERS.items()
    }


@tool
def get_current_date() -> str:
    """Returns the current date and time. Use this when you need to know today's date, calculate deadlines, or answer time-related questions."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S (%A)")


SKILLS_DIR = Path(__file__).parent.parent / "skills"


def load_skills_files():
    """Load all SKILL.md files into a virtual file dict for StateBackend."""
    files = {}
    if SKILLS_DIR.exists():
        for skill_dir in SKILLS_DIR.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text()
                    virtual_path = f"/skills/{skill_dir.name}/SKILL.md"
                    files[virtual_path] = create_file_data(content)
                    logger.info(f"Loaded skill: {skill_dir.name}")
    return files


async def create_crm_agent():
    client = MultiServerMCPClient(get_mcp_config())
    mcp_tools = await client.get_tools()
    logger.info(f"Loaded {len(mcp_tools)} MCP tools: {[t.name for t in mcp_tools]}")
    skills_files = load_skills_files()
    checkpointer = MemorySaver()
    agent = create_deep_agent(
        model="openai:gpt-4o",
        tools=mcp_tools + [get_current_date],
        system_prompt=SYSTEM_PROMPT,
        skills=["/skills/"],
        checkpointer=checkpointer,
    )
    return agent, skills_files
