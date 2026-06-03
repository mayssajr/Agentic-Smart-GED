using Microsoft.EntityFrameworkCore;
using MiniGED.API.Models;
using Npgsql.EntityFrameworkCore.PostgreSQL;

namespace MiniGED.API.Data;

public class ApplicationDbContext : DbContext
{
    public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
        : base(options) { }

    public DbSet<User> Users => Set<User>();
    public DbSet<Role> Roles => Set<Role>();
    public DbSet<UserRole> UserRoles => Set<UserRole>();
    public DbSet<Document> Documents => Set<Document>();
    public DbSet<DocumentFile> DocumentFiles => Set<DocumentFile>();
    public DbSet<DocumentTask> DocumentTasks => Set<DocumentTask>();
    public DbSet<RefreshToken> RefreshTokens => Set<RefreshToken>();
    public DbSet<CandidateApplication> CandidateApplications => Set<CandidateApplication>();   
    public override Task<int> SaveChangesAsync(CancellationToken cancellationToken = default)
    {
        foreach (var entry in ChangeTracker.Entries<BaseModel>())
        {
            if (entry.State == EntityState.Modified)
            {
                entry.Entity.UpdateDate = DateTime.UtcNow;
            }
        }

        return base.SaveChangesAsync(cancellationToken);
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);

        modelBuilder.Entity<Document>()
            .HasMany(d => d.Files)
            .WithOne(f => f.Document)
            .HasForeignKey(f => f.DocumentId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<DocumentFile>()
            .Property(f => f.SearchVector)
            .HasComputedColumnSql(
                @"to_tsvector('simple', coalesce(""SearchableText"", ''))",
                stored: true);

        modelBuilder.Entity<DocumentFile>()
            .HasIndex(f => f.SearchVector)
            .HasMethod("GIN");

        modelBuilder.Entity<Document>()
            .HasMany(d => d.Tasks)
            .WithOne(t => t.Document)
            .HasForeignKey(t => t.DocumentId)
            .OnDelete(DeleteBehavior.Cascade);
        modelBuilder.Entity<User>()
            .HasMany(d => d.UserRoles)
            .WithOne(f => f.User)
            .HasForeignKey(f => f.UserId)
            .OnDelete(DeleteBehavior.Cascade);
        modelBuilder.Entity<Role>()
            .HasMany(d => d.UserRoles)
            .WithOne(f => f.Role)
            .HasForeignKey( f => f.RoleId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<CandidateApplication>()
            .Property(c => c.Status)
            .HasConversion<string>();
    }
}
