const dbName = process.env.MONGO_INITDB_DATABASE || "vigmykd";
const appUser = process.env.MONGO_APP_USER || "vigmykd_app";
const appPass = process.env.MONGO_APP_PASSWORD;

if (appPass) {
  db = db.getSiblingDB(dbName);
  
  db.createUser({
    user: appUser,
    pwd: appPass,
    roles: [
      { role: "readWrite", db: dbName },
      { role: "dbAdmin", db: dbName }
    ]
  });
}