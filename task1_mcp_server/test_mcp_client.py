
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_file = Path(__file__).with_name("server.py")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            print("Available tools:", names)

            assert "get_customer_record" in names
            assert "trigger_refund" in names

            result = await session.call_tool(
                "get_customer_record",
                {"customer_id": "CUST-12345"},
            )

            print("Customer lookup:", result)
            assert not result.isError

            refund = await session.call_tool(
                "trigger_refund",
                {
                    "customer_id": "CUST-12345",
                    "amount": 50.0,
                    "reason": "Product arrived damaged",
                },
            )

            print("Mock refund:", refund)
            assert not refund.isError
            
            # Test invalid refund reason through MCP
            invalid_refund = await session.call_tool(
                "trigger_refund",
                {
                    "customer_id": "CUST-12345",
                    "amount": 50.0,
                    "reason": "Bad",
                },
            )

            print("Invalid refund response:", invalid_refund)

            assert invalid_refund.isError is True, (
                "Expected MCP tool error for invalid reason"
            )

            print("Invalid refund correctly rejected!")
            
            # Test invalid customer ID through MCP
            invalid_customer = await session.call_tool(
                "get_customer_record",
                {
                    "customer_id": "INVALID-ID",
                },
            )

            print("Invalid customer response:", invalid_customer)

            assert invalid_customer.isError is True, (
                "Expected MCP error for invalid customer ID"
            )

            print("Invalid customer ID correctly rejected!")
            
            # Test calling an unknown MCP tool
            from mcp.shared.exceptions import McpError

            try:
                unknown_result = await session.call_tool(
                    "nonexistent_tool",
                    {},
                )

            except McpError as error:
                print("Unknown tool returned MCP protocol error:")
                print(error)

            else:
                print("Unknown tool response:", unknown_result)
                assert unknown_result.isError is True, (
                    "Unknown tool should not succeed"
                )

            print("Unknown tool correctly rejected!")

            print("MCP integration test passed!")


if __name__ == "__main__":
    asyncio.run(main())
