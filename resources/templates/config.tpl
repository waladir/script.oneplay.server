<html>
  <head>
      <title>Oneplay Server</title>
  </head>
  <body>
    <h2>Oneplay Server{{ version }}</h2>
    <table>
% for param in config:
      <tr><td>{{ param }}</td><td>{{ config[param] }}</td></tr>
% end
    </table>
    <br>
    <form action="/">
      <input type="submit" value="Zpět">
    </form>
  </body>
</html>