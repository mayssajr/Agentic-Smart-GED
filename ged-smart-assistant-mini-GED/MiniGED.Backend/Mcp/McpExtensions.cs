using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;
using MiniGED.API.Data;
using MiniGED.API.Interfaces;
using MiniGED.API.Services;

namespace MiniGED.API.Mcp;

public static class McpExtensions
{
    public static async Task<bool> RunMcpIfRequestedAsync(
        string[] args,
        IConfiguration configuration)
    {
        if (!args.Contains("--mcp"))
            return false;

        Console.Error.WriteLine("[MiniGED MCP] Mode stdio activé");
        Console.Error.WriteLine("[MiniGED MCP] Outils : get_documents, get_document, " +
            "get_document_text, search_documents, create_document, get_file_status");

        var mcpBuilder = Host.CreateEmptyApplicationBuilder(new HostApplicationBuilderSettings
        {
            Args = args,
        });

        mcpBuilder.Logging
            .ClearProviders()
            .AddConsole(opts =>
            {
                opts.LogToStandardErrorThreshold = LogLevel.Trace;
            })
            .SetMinimumLevel(LogLevel.Warning);  

        var connectionString = configuration.GetConnectionString("DefaultConnection");
        mcpBuilder.Services.AddDbContext<ApplicationDbContext>(opts =>
            opts.UseNpgsql(connectionString)
                .EnableSensitiveDataLogging(false)
                .LogTo(_ => { }, LogLevel.None));

        mcpBuilder.Services.AddScoped<IDocumentSearchService, DocumentSearchService>();

        mcpBuilder.Services
            .AddMcpServer()
            .WithStdioServerTransport()
            .WithToolsFromAssembly();

        var mcpHost = mcpBuilder.Build();
        await mcpHost.RunAsync();

        return true;
    }
}