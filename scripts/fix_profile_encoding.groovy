@GrabConfig(systemClassLoader=true)
@Grab(group='org.postgresql', module='postgresql',  version='9.4-1205-jdbc42')
@Grab(group='org.pac4j', module='pac4j-core', version='3.3.0')
@Grab(group='org.pac4j', module='pac4j-sql', version='3.3.0')
@Grab(group='com.fasterxml.jackson.core', module='jackson-core', version='2.13.4')
@Grab(group='com.fasterxml.jackson.core', module='jackson-annotations', version='2.13.4')
@Grab(group='com.fasterxml.jackson.core', module='jackson-databind', version='2.13.4')
@Grab(group='ch.qos.logback', module='logback-classic', version='1.0.13')
import groovy.sql.Sql
import org.pac4j.sql.profile.DbProfile
import org.pac4j.core.util.JavaSerializationHelper
import com.fasterxml.jackson.annotation.JsonAutoDetect
import com.fasterxml.jackson.annotation.PropertyAccessor
import com.fasterxml.jackson.core.JsonProcessingException
import com.fasterxml.jackson.databind.ObjectMapper

public class JsonSerializer {

    private ObjectMapper objectMapper

    public JsonSerializer() {
        objectMapper = new ObjectMapper();
        objectMapper.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.NONE);
        objectMapper.setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY);
    }

    public String encode(final Object obj) {
        if (obj == null) {
            return null;
        }
        return objectMapper.writeValueAsString(obj);
    }
}

class Profile {
    String id;
    String serializedProfile;
    boolean updated = false;

    Profile(id, serializedProfile) {
        this.id = id
        this.serializedProfile = serializedProfile
    }

    void recode(JavaSerializationHelper helper, JsonSerializer serializer) {
        println this.serializedProfile
        if (this.serializedProfile.startsWith("{")) {
            println "Profile already in JSON format"
            return
        }
        DbProfile decoded = helper.unserializeFromBase64(this.serializedProfile)
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

JavaSerializationHelper helper = new JavaSerializationHelper()
JsonSerializer serializer = new JsonSerializer()
def updateSql = "UPDATE users SET serializedprofile = ? where id = ?"
con.withTransaction {
    profiles.each { profile ->
        profile.recode(helper, serializer)
        if (profile.updated) {
            con.execute updateSql, [profile.serializedProfile, profile.id]
        }
    }
}

