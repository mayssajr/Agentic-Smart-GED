namespace MiniGED.API.Services
{
    using System;
    using Microsoft.EntityFrameworkCore;
    using MiniGED.API.Data;
    using MiniGED.API.Models;

    public static class SeedData
    {
        

        public static async System.Threading.Tasks.Task SeedAsync(ApplicationDbContext db, PasswordService passwordService)
        {
            // Ensure DB exists
            //await db.Database.MigrateAsync();

            // 1. Create roles if missing
            var roles = new[] { "Admin", "User" };
            foreach (var roleName in roles)
            {
                if (!await db.Roles.AnyAsync(r => r.Name == roleName))
                {
                    db.Roles.Add(new Role { Name = roleName });
                }
            }
            await db.SaveChangesAsync();

            // 2. Create admin user if missing
            var adminEmail = "admin@ged.local";
            var admin = await db.Users.FirstOrDefaultAsync(u => u.Email == adminEmail);
            if (admin == null)
            {
                admin = new User
                {
                 
                    Username = "admin",
                    FullName = "System Administrator",
                    Email = adminEmail,
                    PasswordHashed = passwordService.HashPassword( "Admin123!"),
                    PhoneNumber = "+216 52 023 467"
                 
                };
                db.Users.Add(admin);
                await db.SaveChangesAsync();
            }

            // 3. Assign Admin role to admin user
            var adminRole = await db.Roles.FirstAsync(r => r.Name == "Admin");
            if (!await db.UserRoles.AnyAsync(ur => ur.UserId == admin.Id && ur.RoleId == adminRole.Id))
            {
                db.UserRoles.Add(new UserRole { UserId = admin.Id, RoleId = adminRole.Id });
                await db.SaveChangesAsync();
            }

            // 4. Ensure all users have User role
            var userRole = await db.Roles.FirstAsync(r => r.Name == "User");
            var usersWithoutUserRole = await db.Users
                .Where(u => !db.UserRoles.Any(ur => ur.UserId == u.Id && ur.RoleId == userRole.Id))
                .ToListAsync();

            foreach (var u in usersWithoutUserRole)
            {
                db.UserRoles.Add(new UserRole { UserId = u.Id, RoleId = userRole.Id });
            }
            if (usersWithoutUserRole.Any())
                await db.SaveChangesAsync();
        }
    }
}
