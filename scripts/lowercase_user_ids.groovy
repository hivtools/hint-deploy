// See ticket
// https://mrc-ide.myjetbrains.com/youtrack/issue/mrc-3845
// for details

@GrabConfig(systemClassLoader=true)
@Grab(group='org.postgresql', module='postgresql',  version='9.4-1205-jdbc42')
@Grab(group='ch.qos.logback', module='logback-classic', version='1.0.13')
import groovy.sql.Sql

class Profile {
    def con;
    String old_id;
    String new_id;

    Profile(id) {
        this.old_id = id
        this.new_id = toLowerCase(this.old_id)
    }

    void migrate() {
        if (this.con.firstRow('SELECT count(*) as cnt FROM users WHERE id =:id', id:new_id)?.cnt > 0) {
            println "Not migrating " + this.old_id + " as account already exists for id " + this.new_id
            return
        }
        def updateSql = "INSERT into users (id, username) VALUES (:new_id, :new_id);
        UPDATE user_session set user_id = :new_id where user_id = :old_id;
        UPDATE adr_key set user_id = :new_id where user_id = :old_id;
        UPDATE project set shared_by = :new_id where user_id = :old_id;
        UPDATE project set user_id = :new_id where user_id = :old_id;

        DELETE from users where id = :old_id;"
        //con.execute([new_id: this.new_id, old_id: this.new_id], updateSql)
        println "Migrated " + this.old_id + " to " + this.new_id
        return
    }
}

def dbUrl      = "jdbc:postgresql://hint_db/hint"
def dbUser     = "hintuser"
def dbPassword = "changeme"
def dbDriver   = "org.postgresql.Driver"
def con = Sql.newInstance(dbUrl, dbUser, dbPassword, dbDriver)

def users = []
try {
    con.eachRow("SELECT id FROM users WHERE id ~ '[A-Z]';") { row ->
        users << new Profile(con, row.id)
    }

    con.withTransaction {
        users.each { user ->
            user.migrate()
        }
    }
} finally {
    con.close()
}
