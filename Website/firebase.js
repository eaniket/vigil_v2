(function () {
  const config = {
    apiKey: "AIzaSyCKc3EmsQUim9LQc29C0JiTPGj1ErvQY6I",
    authDomain: "vigil-15d90.firebaseapp.com",
    databaseURL: "https://vigil-15d90.firebaseio.com",
    projectId: "vigil-15d90",
    storageBucket: "vigil-15d90.appspot.com",
    messagingSenderId: "915294142360",
    appId: "1:915294142360:web:15e16c76f439bf885e35ed"
  };

  firebase.initializeApp(config);
}());

const pol = document.getElementById("police");
const dbRef = firebase.database().ref().child("Police");
dbRef.on("value", snap => pol.innerText = snap.val());
const med = document.getElementById("med");
const dbRef1 = firebase.database().ref().child("Medical");
dbRef1.on("value", snap => med.innerText = snap.val());
const fire = document.getElementById("fire");
const dbRef2 = firebase.database().ref().child("FireDept");
dbRef2.on("value", snap => fire.innerText = snap.val());
const fhelp = document.getElementById("fires");
const mhelp = document.getElementById("meds");
const phelp = document.getElementById("polices");
const dbrefloc = firebase.database().ref('help')
dbrefloc.child("medical").on("value", snap => mhelp.innerText = snap.val())
dbrefloc.child("police").on("value", snap => phelp.innerText = snap.val())
dbrefloc.child("fire").on("value", snap => fhelp.innerText = snap.val())


var storage = firebase.storage();
var storageRef = storage.ref();



storageRef.child('images/foo.jpg').getDownloadURL().then(function (url) {
  var test = url;
  document.getElementById("graph").src = test;
}).catch(function (error) {

});

storageRef.child('images/bar.jpg').getDownloadURL().then(function (url) {
  var test = url;
  document.getElementById("frame1").src = test;

}).catch(function (error) {

});
storageRef.child('images/foobar.jpg').getDownloadURL().then(function (url) {
  var test = url;
  document.getElementById("frame2").src = test;

}).catch(function (error) {

});


function assignf() {
  firebase.database().ref('help').child("fire").set("Assigned");
  fhelp.style.backgroundColor = "green";
}

function assignm() {
  firebase.database().ref('help').child("medical").set("Assigned");
  mhelp.style.backgroundColor = "green";
}

function assignp() {
  firebase.database().ref('help').child("police").set("Assigned");
  phelp.style.backgroundColor = "green";
}

function resetData() {
  fhelp.style.backgroundColor = "blueviolet";
  phelp.style.backgroundColor = "blueviolet";
  mhelp.style.backgroundColor = "blueviolet";
  firebase.database().ref('Police').set(0);
  firebase.database().ref('Medical').set(0);
  firebase.database().ref('FireDept').set(0);
  firebase.database().ref('help').child("fire").set("Unassigned");
  firebase.database().ref('help').child("medical").set("Unassigned");
  firebase.database().ref('help').child("police").set("Unassigned");
}
