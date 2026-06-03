using System.Text;
using Hangfire;
using Hangfire.Storage.SQLite;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using MiniGED.API.Config;
using MiniGED.API.Data;
using MiniGED.API.Interfaces;
using MiniGED.API.Mcp;          
using MiniGED.API.Services;

if (await McpExtensions.RunMcpIfRequestedAsync(args,
        new ConfigurationBuilder()
            .SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: false)
            .AddJsonFile($"appsettings.{Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT") ?? "Production"}.json", optional: true)
            .AddEnvironmentVariables()
            .Build()))
    return;

async Task EnsureUserRolesAuditColumns(ApplicationDbContext db)
{
    try
    {
        var connection = db.Database.GetDbConnection();
        await connection.OpenAsync();

        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'UserRoles' AND column_name = 'CreateDate'
            """;

        var createDateExists = await command.ExecuteScalarAsync() != null;
        if (!createDateExists)
        {
            command.CommandText = """ALTER TABLE "UserRoles" ADD COLUMN "CreateDate" timestamp NOT NULL DEFAULT NOW()""";
            await command.ExecuteNonQueryAsync();
        }

        command.CommandText = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'UserRoles' AND column_name = 'UpdateDate'
            """;

        var updateDateExists = await command.ExecuteScalarAsync() != null;
        if (!updateDateExists)
        {
            command.CommandText = """ALTER TABLE "UserRoles" ADD COLUMN "UpdateDate" timestamp NULL""";
            await command.ExecuteNonQueryAsync();
        }
    }
    catch (Exception ex)
    {
        Console.WriteLine($"Error ensuring UserRoles audit columns: {ex.Message}");
    }
    finally
    {
        await db.Database.CloseConnectionAsync();
    }
}

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyOrigin()
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo
    {
        Version = "v1",
        Title = "MiniGed API",
        Description = "An ASP.NET Core Web API for managing electronic documents",
        TermsOfService = new Uri("https://example.com/terms"),
        Contact = new OpenApiContact
        {
            Name = "Example Contact",
            Url = new Uri("https://example.com/contact")
        },
        License = new OpenApiLicense
        {
            Name = "Example License",
            Url = new Uri("https://example.com/license")
        }
    });
    options.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        In = ParameterLocation.Header,
        Description = "Please enter a valid token",
        Name = "Authorization",
        Type = SecuritySchemeType.Http,
        BearerFormat = "JWT",
        Scheme = "Bearer"
    });
    options.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecurityScheme
            {
                Reference = new OpenApiReference
                {
                    Type = ReferenceType.SecurityScheme,
                    Id = "Bearer"
                }
            },
            Array.Empty<string>()
        }
    });
});

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
var hangfireConnectionString = builder.Configuration.GetConnectionString("HangfireConnection");

builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseNpgsql(connectionString));

builder.Services.AddScoped<TokenService>();
builder.Services.AddScoped<LoginUserWithRefreshToken>();
builder.Services.AddScoped<IDocumentTextExtractor, DocumentTextExtractor>();
builder.Services.AddScoped<IDocumentSearchService, DocumentSearchService>();
builder.Services.AddScoped<IFileProcessingJob, FileProcessingJob>();
builder.Services.AddScoped<IFileService, FileService>();
builder.Services.AddScoped<PasswordService>();

builder.Services.AddHttpClient();

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = false,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Key"]!))
        };
    });

builder.Services.AddHangfire(config => config
    .SetDataCompatibilityLevel(CompatibilityLevel.Version_180)
    .UseSimpleAssemblyNameTypeSerializer()
    .UseRecommendedSerializerSettings()
    .UseSQLiteStorage(hangfireConnectionString));

builder.Services.AddHangfireServer();
builder.Services.AddControllers();
builder.Services.AddScoped<AceReflectJob>();


var app = builder.Build();

// ── Pipeline HTTP normal (inchangé) ──────────────────────────────────────────
app.UseCors("AllowAll");
new LoginUserWithRefreshToken.Endpoint().MapEndpoint(app);
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
    app.UseHangfireDashboard();
    app.MapHangfireDashboard("/hangfire");

    RecurringJob.AddOrUpdate<AceReflectJob>(
    "ace-daily-reflect",
    job => job.RunDailyReflectionAsync(),
    "0 3 * * *" );
}

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
    var pw = scope.ServiceProvider.GetRequiredService<PasswordService>();

    await db.Database.MigrateAsync();
    await EnsureUserRolesAuditColumns(db);
    await SeedData.SeedAsync(db, pw);
}

app.Run();