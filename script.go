package main

import "fmt"
import "io/ioutil"
import "net/http"


// https://golang.org/pkg/net/http/
func getExample() string {
	resp, err := http.Get("http://example.com/")
	if err != nil {
		// handle error
	}

	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		// handle error
	}

	return string(body[:len(body)])
}


func main() {
    fmt.Println(getExample())
}
