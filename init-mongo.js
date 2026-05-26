const dbName = "vigmykd";
const appUser = "vigmykd_app";
const appPass = "" // replace

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