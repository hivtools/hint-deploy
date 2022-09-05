import groovy.sql.Sql 

println "Hello World"

def dbUrl      = "jdbc:postgresql://hint_db/hint"
def dbUser     = "postgres"
def dbPassword = "password"
def dbDriver   = "org.postgresql.Driver"

def con = Sql.newInstance(dbUrl, dbUser, dbPassword, dbDriver)

println con.execute("SELECT count(*) from users")
