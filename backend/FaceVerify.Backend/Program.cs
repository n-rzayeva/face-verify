using FaceVerify.Backend.Data;
using FaceVerify.Backend.Services;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("DefaultConnection")));
builder.Services.AddHttpClient<MlApiService>(client =>
{
    client.BaseAddress = new Uri(builder.Configuration["MlApi:BaseUrl"]!);
    client.Timeout = TimeSpan.FromSeconds(30);
});
builder.Services.AddScoped<JwtService>();
builder.Services.AddScoped<VerificationService>();

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();


var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    db.Database.EnsureCreated();
}

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.MapControllers();
app.Run();