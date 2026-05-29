using FaceVerify.Backend.Models;
using Microsoft.EntityFrameworkCore;

namespace FaceVerify.Backend.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<VerificationFrame> VerificationFrames { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<VerificationFrame>(entity =>
        {
            entity.HasKey(e => e.SessionId);
            entity.Property(e => e.BestFrame).IsRequired();
            entity.Property(e => e.ExpiresAt).IsRequired();
        });
    }
}