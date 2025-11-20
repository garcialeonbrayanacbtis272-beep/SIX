function agregarproducto(){
    let producto =`
    <div class="row p-3">
        <div class="col-8 m-3 p-3 border border-1">
            <div class="row">
                <div class="col"><img src="./assets/00019425351617l.webp" alt=""></div>
                <div class="col">1</div>
                <div class="col">Airpods pro Apple 2nd Generacion</div>
                <div class="col">$3,999.00</div>
                </div>
            </div>
        </div>
        `;
        document.getElementById("carrito").innerHTML += producto;
}