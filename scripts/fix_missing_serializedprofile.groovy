// We have upgraded pac4j from v 3.3.0 to v 5.4.3 see
// https://github.com/mrc-ide/hint/pull/731/files, the update includes changes
// to the serialization format used for the profile. It previously used
// java serialization but now uses JSON. Support for Java serialized profiles
// has been removed meaning that when a user with an old format profile tries to
// login they get an error.
// We need to migrate the profile to use JSON serialization.
// This script reads the profiles from the database, uses the
// ProfleServiceSerializer from pac4j to decode the Java serialized profile
// and recode as JSON. It then updates the column in the database to the JSON
// serialized format.

@GrabConfig(systemClassLoader=true)
@Grab(group='org.postgresql', module='postgresql',  version='9.4-1205-jdbc42')
@Grab(group='org.pac4j', module='pac4j-sql', version='3.9.0')
@Grab(group='org.pac4j', module='pac4j-core', version='3.9.0')
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

    void serialize(ProfileServiceSerializer serializer) {
        println this.serializedProfile
        if (length(this.serializedProfile) > 0) {
            println "Not updating as profile already serialized"
            return
        }
        DbProfile profile = DbProfile()
        profile.build(this.id, mapOf("username" to this.id))
        this.serializedProfile = serializer.encode(decoded)
        println "Serialized profile"
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
try {
    con.eachRow("SELECT id, serializedprofile from users;") { row ->
        profiles << new Profile(row.id, row.serializedprofile)
    }
    ProfileServiceSerializer serializer = new ProfileServiceSerializer(DbProfile.class)
    def updateSql = "UPDATE users SET serializedprofile = ? where id = ?"
    con.withTransaction {
        profiles.each { profile ->
            profile.serialize()
            if (false) {
                con.execute updateSql, [profile.serializedProfile, profile.id]
            }
        }
    }
} finally {
    con.close()
}
