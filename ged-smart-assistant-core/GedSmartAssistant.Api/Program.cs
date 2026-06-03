using GedSmartAssistant.Api.Interfaces;
using GedSmartAssistant.Api.Models.Configuration;
using GedSmartAssistant.Api.Services;
using Microsoft.Extensions.Options;
using System.Text.Json; 

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers()
    .AddJsonOptions(opts =>
    {
        opts.JsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    });
    
builder.Services.AddAuthorization();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddOpenApi();

builder.Services.Configure<AiServiceOptions>(builder.Configuration.GetSection(AiServiceOptions.SectionName));
builder.Services.Configure<MiniGedOptions>(builder.Configuration.GetSection(MiniGedOptions.SectionName));
builder.Services.Configure<AssistantFrontendOptions>(builder.Configuration.GetSection(AssistantFrontendOptions.SectionName));

builder.Services.AddHttpContextAccessor();
builder.Services.AddCors(options =>
{
    options.AddPolicy("AssistantFrontend", policy =>
    {
        var allowedOrigins = builder.Configuration
            .GetSection($"{AssistantFrontendOptions.SectionName}:AllowedOrigins")
            .Get<string[]>() ?? [];

        if (allowedOrigins.Length > 0)
        {
            policy.WithOrigins(allowedOrigins)
                .AllowAnyHeader()
                .AllowAnyMethod()
                .WithExposedHeaders("X-Ged-Access-Token", "X-Ged-Refresh-Token")
                .AllowCredentials();
            return;
        }

        policy.SetIsOriginAllowed(_ => true)
            .AllowAnyHeader()
            .AllowAnyMethod()
            .WithExposedHeaders("X-Ged-Access-Token", "X-Ged-Refresh-Token")
            .AllowCredentials();
    });
});

builder.Services.AddHttpClient<IAiInferenceClient, AiInferenceClient>((serviceProvider, client) =>
{
    var options = serviceProvider.GetRequiredService<IOptions<AiServiceOptions>>().Value;
    client.BaseAddress = new Uri(options.BaseUrl);
});

builder.Services.AddHttpClient<IMiniGedApiClient, MiniGedApiClient>((serviceProvider, client) =>
{
    var options = serviceProvider.GetRequiredService<IOptions<MiniGedOptions>>().Value;
    client.BaseAddress = new Uri(options.BaseUrl);
});

builder.Services.AddScoped<ISessionTokenStore, SessionTokenStore>();
builder.Services.AddScoped<IMiniGedSessionService, MiniGedSessionService>();
builder.Services.AddScoped<IChatService, ChatService>();

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseCors("AssistantFrontend");
app.UseAuthorization();
app.MapControllers();

app.Run();
