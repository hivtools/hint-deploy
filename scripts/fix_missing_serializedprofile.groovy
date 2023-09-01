// Since switching to login via SSO when a new account is created
// it does not set up a serializedprofile in the db for the new account
// this then means that users cannot share projects with those new users
// this script will create a serialized profile for each user where it
// is empty and then save it to the database

@GrabConfig(systemClassLoader=true)
@Grab(group='org.postgresql', module='postgresql',  version='9.4-1205-jdbc42')
@Grab(group='org.pac4j', module='pac4j-sql', version='3.9.0')
@Grab(group='org.pac4j', module='pac4j-core', version='3.9.0')
@Grab(group='ch.qos.logback', module='logback-classic', version='1.0.13')
import groovy.sql.Sql
import org.pac4j.sql.profile.DbProfile
import org.pac4j.core.util.serializer.ProfileServiceSerializer

class Profile {
    Object id;
    String serializedProfile;
    boolean updated = false;

    Profile(id, serializedProfile) {
        this.id = id
        this.serializedProfile = serializedProfile
    }

    void serialize(ProfileServiceSerializer serializer) {
        println "Current serializedprofile is"
        println this.serializedProfile
        if (this.serializedProfile?.length() > 0) {
            println "Not updating as profile already serialized"
            return
        }
        DbProfile profile = new DbProfile()
        profile.build(this.id, ["username": this.id])
        this.serializedProfile = serializer.encode(profile)
        println "Updated serialized profile is"
        println this.serializedProfile
        this.updated = true;
    }
}

def dbUrl      = "jdbc:postgresql://hint-db/hint"
def dbUser     = "hintuser"
def dbPassword = "changeme"
def dbDriver   = "org.postgresql.Driver"
def con = Sql.newInstance(dbUrl, dbUser, dbPassword, dbDriver)

def profiles = []
try {
    con.eachRow("SELECT id, serializedprofile from users;") { row ->
        profiles << new Profile(row.id, row.serializedprofile)
    }
    ProfileServiceSerializer serializer = new ProfileServiceSerializer(DbProfile.class)
    def updateSql = "UPDATE users SET serializedprofile = ? where id = ?"
    con.withTransaction {
        profiles.each { profile ->
            profile.serialize(serializer)
            if (profile.updated) {
                con.execute updateSql, [profile.serializedProfile, profile.id]
            }
        }
    }
} finally {
    con.close()
}
