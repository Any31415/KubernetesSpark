import com.sun.net.httpserver.{HttpServer, HttpExchange, HttpHandler}
import java.net.InetSocketAddress
import java.sql.{Connection, DriverManager, ResultSet}
import java.io.OutputStream
import scala.io.Source

object Main {

  val jdbcUrl = "jdbc:mysql://localhost:3306/off_clustering"
  val dbUser = "lab6user"
  val dbPassword = "lab2"

  def getConnection(): Connection = {
    Class.forName("com.mysql.cj.jdbc.Driver")
    DriverManager.getConnection(jdbcUrl, dbUser, dbPassword)
  }

  class DataHandler extends HttpHandler {
    def handle(exchange: HttpExchange): Unit = {
      if (exchange.getRequestMethod == "GET") {
        val conn = getConnection()
        val stmt = conn.createStatement()
        val rs: ResultSet = stmt.executeQuery(
          """SELECT id, energy_kcal_100g, fat_100g, saturated_fat_100g,
            |carbohydrates_100g, sugars_100g, proteins_100g, salt_100g, fiber_100g
            |FROM products
            |WHERE NOT (energy_kcal_100g = 0 AND fat_100g = 0 AND saturated_fat_100g = 0
            |  AND carbohydrates_100g = 0 AND sugars_100g = 0 AND proteins_100g = 0
            |  AND salt_100g = 0 AND fiber_100g = 0)""".stripMargin
        )

        val sb = new StringBuilder("[")
        var first = true
        while (rs.next()) {
          if (!first) sb.append(",")
          first = false
          sb.append(s"""{"id":${rs.getInt("id")},""" +
            s""""energy_kcal_100g":${rs.getDouble("energy_kcal_100g")},""" +
            s""""fat_100g":${rs.getDouble("fat_100g")},""" +
            s""""saturated_fat_100g":${rs.getDouble("saturated_fat_100g")},""" +
            s""""carbohydrates_100g":${rs.getDouble("carbohydrates_100g")},""" +
            s""""sugars_100g":${rs.getDouble("sugars_100g")},""" +
            s""""proteins_100g":${rs.getDouble("proteins_100g")},""" +
            s""""salt_100g":${rs.getDouble("salt_100g")},""" +
            s""""fiber_100g":${rs.getDouble("fiber_100g")}}""")
        }
        sb.append("]")

        rs.close(); stmt.close(); conn.close()

        val response = sb.toString()
        exchange.getResponseHeaders.add("Content-Type", "application/json")
        exchange.sendResponseHeaders(200, response.getBytes("UTF-8").length)
        val os: OutputStream = exchange.getResponseBody
        os.write(response.getBytes("UTF-8"))
        os.close()
      } else {
        exchange.sendResponseHeaders(405, -1)
      }
    }
  }

  class ResultsHandler extends HttpHandler {
    def handle(exchange: HttpExchange): Unit = {
      if (exchange.getRequestMethod == "POST") {
        val body = Source.fromInputStream(exchange.getRequestBody, "UTF-8").mkString

        val pattern = """\{"product_id":(\d+),"cluster":(\d+)\}""".r
        val records = pattern.findAllMatchIn(body).map(m => (m.group(1).toInt, m.group(2).toInt)).toList

        val conn = getConnection()
        val pstmt = conn.prepareStatement("INSERT INTO cluster_results (product_id, cluster) VALUES (?, ?)")
        records.foreach { case (productId, cluster) =>
          pstmt.setInt(1, productId)
          pstmt.setInt(2, cluster)
          pstmt.addBatch()
        }
        pstmt.executeBatch()
        pstmt.close(); conn.close()

        val response = s"""{"status":"ok","inserted":${records.length}}"""
        exchange.getResponseHeaders.add("Content-Type", "application/json")
        exchange.sendResponseHeaders(200, response.getBytes("UTF-8").length)
        val os = exchange.getResponseBody
        os.write(response.getBytes("UTF-8"))
        os.close()
      } else {
        exchange.sendResponseHeaders(405, -1)
      }
    }
  }

  class ViewHandler extends HttpHandler {
    def handle(exchange: HttpExchange): Unit = {
      val conn = getConnection()
      val stmt = conn.createStatement()
      val rs = stmt.executeQuery(
        "SELECT product_id, cluster, created_at FROM cluster_results ORDER BY created_at DESC LIMIT 50"
      )
      val sb = new StringBuilder(
        """<html><body><h2>Последние 50 предсказаний</h2>
        |<form method="POST" action="/clear"><button type="submit">Очистить cluster_results</button></form>
        |<table border='1'>""".stripMargin)
      sb.append("<tr><th>Product ID</th><th>Cluster</th><th>Created At</th></tr>")
      while (rs.next()) {
        sb.append(s"""<tr><td>${rs.getInt("product_id")}</td><td>${rs.getInt("cluster")}</td><td>${rs.getTimestamp("created_at")}</td></tr>""")
      }
      sb.append("</table></body></html>")
      rs.close(); stmt.close(); conn.close()

      val response = sb.toString()
      exchange.getResponseHeaders.add("Content-Type", "text/html; charset=UTF-8")
      exchange.sendResponseHeaders(200, response.getBytes("UTF-8").length)
      val os = exchange.getResponseBody
      os.write(response.getBytes("UTF-8"))
      os.close()
    }
  }

  class ClearHandler extends HttpHandler {
    def handle(exchange: HttpExchange): Unit = {
      if (exchange.getRequestMethod == "POST") {
        val conn = getConnection()
        val stmt = conn.createStatement()
        stmt.executeUpdate("TRUNCATE TABLE cluster_results")
        stmt.close(); conn.close()

        exchange.getResponseHeaders.add("Location", "/view")
        exchange.sendResponseHeaders(302, -1)
        exchange.close()
      } else {
        exchange.sendResponseHeaders(405, -1)
      }
    }
  }

  def main(args: Array[String]): Unit = {
    val server = HttpServer.create(new InetSocketAddress(8080), 0)
    server.createContext("/data", new DataHandler())
    server.createContext("/results", new ResultsHandler())
    server.createContext("/view", new ViewHandler())
    server.createContext("/clear", new ClearHandler())
    server.setExecutor(null)
    server.start()
    println("Витрина данных запущена на http://localhost:8080")
    println("GET  /data    — выгрузка данных продуктов")
    println("POST /results — приём предсказаний кластеризации")
    println("GET  /view    — HTML-таблица последних предсказаний")
    println("Нажмите Enter для остановки...")
    scala.io.StdIn.readLine()
    server.stop(0)
  }
}