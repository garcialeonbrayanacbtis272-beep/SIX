function agregar Producto(){

let producto =

<div class="row p-3">

<div class="col-8 m-3 p-3 border border-1">

<div class="row">

<div class="col"><img src="assets/celular.jpg" alt=""></div>

<div class="col">1</div>

<div class="col">Smartphone Apple</div>

<div class="col">$15.00</div>

</div>

</div>

</div>

;

document.getElementById("carrito").innerHTML += producto; }