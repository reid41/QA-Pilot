package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"strings"
)

type Node struct {
	Name     string
	Type     string   // "func", "method", "type", "interface", "int", or "import"
	Calls    []string // list of called functions/methods
	Code     string   // source code of the node
	Position string   // file position of the node
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: ./parser <path_to_go_file>")
		os.Exit(1)
	}

	filePath := os.Args[1]
	fset := token.NewFileSet()
	node, err := parser.ParseFile(fset, filePath, nil, parser.ParseComments)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	nodes := make(map[string]*Node)
	ast.Inspect(node, func(n ast.Node) bool {
		switch x := n.(type) {
		case *ast.FuncDecl:
			funcName := x.Name.Name
			funcType := "func"
			if x.Recv != nil {
				recvType := fmt.Sprintf("%s", x.Recv.List[0].Type)
				if len(recvType) > 1 && recvType[0] == '*' {
					recvType = recvType[1:]
				}
				funcType = "method"
				funcName = fmt.Sprintf("%s.%s", cleanType(recvType), funcName)
			}
			pos := fset.Position(x.Pos())
			code := getNodeCode(fset, x.Pos(), x.End(), filePath)
			nodes[funcName] = &Node{
				Name:     funcName,
				Type:     funcType,
				Calls:    []string{},
				Code:     code,
				Position: pos.String(),
			}
		case *ast.GenDecl:
			if x.Tok == token.TYPE {
				for _, spec := range x.Specs {
					typeSpec := spec.(*ast.TypeSpec)
					typeName := typeSpec.Name.Name
					pos := fset.Position(typeSpec.Pos())
					code := getNodeCode(fset, typeSpec.Pos(), typeSpec.End(), filePath)
					nodes[typeName] = &Node{
						Name:     typeName,
						Type:     "type",
						Calls:    []string{},
						Code:     code,
						Position: pos.String(),
					}
				}
			} else if x.Tok == token.IMPORT {
				for _, spec := range x.Specs {
					importSpec := spec.(*ast.ImportSpec)
					importPath := importSpec.Path.Value
					pos := fset.Position(importSpec.Pos())
					code := importSpec.Path.Value
					nodes[importPath] = &Node{
						Name:     importPath,
						Type:     "import",
						Calls:    []string{},
						Code:     code,
						Position: pos.String(),
					}
				}
			}
		}
		return true
	})

	// Collect function and method calls
	ast.Inspect(node, func(n ast.Node) bool {
		switch x := n.(type) {
		case *ast.CallExpr:
			caller := ""
			if sel, ok := x.Fun.(*ast.SelectorExpr); ok {
				if ident, ok := sel.X.(*ast.Ident); ok {
					caller = fmt.Sprintf("%s.%s", ident.Name, sel.Sel.Name)
				}
			} else if ident, ok := x.Fun.(*ast.Ident); ok {
				caller = ident.Name
			}
			if caller != "" {
				if parentFunc := getParentFunc(node, x.Pos(), fset); parentFunc != "" {
					if _, ok := nodes[parentFunc]; ok {
						nodes[parentFunc].Calls = append(nodes[parentFunc].Calls, caller)
					}
				}
			}
		}
		return true
	})

	jsonOutput, err := json.Marshal(nodes)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	fmt.Println(string(jsonOutput))
}

func getNodeCode(fset *token.FileSet, start, end token.Pos, filePath string) string {
	startOffset := fset.Position(start).Offset
	endOffset := fset.Position(end).Offset
	code, _ := os.ReadFile(filePath)
	return string(code[startOffset:endOffset])
}

func getParentFunc(node *ast.File, pos token.Pos, fset *token.FileSet) string {
	var parentFunc string
	ast.Inspect(node, func(n ast.Node) bool {
		if fd, ok := n.(*ast.FuncDecl); ok {
			if fd.Pos() < pos && fd.End() > pos {
				if fd.Recv != nil {
					recvType := fmt.Sprintf("%s", fd.Recv.List[0].Type)
					if len(recvType) > 1 && recvType[0] == '*' {
						recvType = recvType[1:]
					}
					parentFunc = fmt.Sprintf("%s.%s", cleanType(recvType), fd.Name.Name)
				} else {
					parentFunc = fd.Name.Name
				}
				return false
			}
		}
		return true
	})
	return parentFunc
}

func cleanType(typeName string) string {
	// Remove generic type parameters if present
	return strings.TrimSpace(strings.Split(typeName, "[")[0])
}
