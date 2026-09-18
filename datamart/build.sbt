ThisBuild / scalaVersion := "2.13.12"

lazy val root = (project in file("."))
  .settings(
    name := "datamart",
    libraryDependencies += "com.mysql" % "mysql-connector-j" % "8.3.0"
  )