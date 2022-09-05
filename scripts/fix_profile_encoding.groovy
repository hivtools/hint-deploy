@GrabConfig(systemClassLoader=true)
@Grab(group='org.postgresql', module='postgresql',  version='9.4-1205-jdbc42')
@Grab(group='org.pac4j', module='pac4j-core', version='3.9.0')
@Grab(group='org.pac4j', module='pac4j-sql', version='3.9.0')
@Grab(group='ch.qos.logback', module='logback-classic', version='1.0.13')
import groovy.sql.Sql
import org.pac4j.sql.profile.DbProfile
import org.pac4j.core.util.serializer.ProfileServiceSerializer

class Profile {
    String id;
    String serializedProfile;
    boolean updated = false;

    Profile(id, serializedProfile) {
        this.id = id
        this.serializedProfile = serializedProfile
    }

    void recode(ProfileServiceSerializer serializer) {
        println this.serializedProfile
        if (this.serializedProfile.startsWith("{")) {
            println "Not migrating as already in JSON format"
            return
        }
        DbProfile decoded = serializer.decode(this.serializedProfile)
        this.serializedProfile = serializer.encode(decoded)
        println "Migrated to JSON format"
        println this.serializedProfile
        this.updated = true;
    }
}

def dbUrl      = "jdbc:postgresql://hint_db/hint"
def dbUser     = "hintuser"
def dbPassword = "changeme"
def dbDriver   = "org.postgresql.Driver"
def con = Sql.newInstance(dbUrl, dbUser, dbPassword, dbDriver)

def profiles = []
con.eachRow("SELECT id, serializedprofile from users;") { row ->
    profiles << new Profile(row.id, row.serializedprofile)
}

ProfileServiceSerializer serializer = new ProfileServiceSerializer(DbProfile.class)
def updateSql = "UPDATE users SET serializedprofile = ? where id = ?"
con.withTransaction {
    profiles.each { profile ->
        profile.recode(serializer)
        if (profile.updated) {
            con.execute updateSql, [profile.serializedProfile, profile.id]
        }
    }
}

