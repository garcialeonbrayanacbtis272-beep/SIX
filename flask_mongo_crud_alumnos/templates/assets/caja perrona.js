
    var producto1=1
    var producto2=1
    var producto3=1
    producto1= parseFloat(prompt("precio producto1"))
    document.write("producto1" + producto1 + "<br>")
    producto2= parseFloat(prompt("precio producto2"))
    document.write("producto2" + producto2 + "<br>")
    producto3= parseFloat(prompt("precio producto3"))
    document.write("producto3" + producto3 + "<br>")
    var subtotal=producto1 + producto2 + producto3;
    var iva=subtotal*0.16;
    var total=subtotal + iva;
    document.write("subtotal"+subtotal+"<br>");
    document.write("iva"+iva+"<br>");
    document.write("total"+total+"<br>");
    

    
