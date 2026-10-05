word1 = input("Enter first word: ")
word2 = input("Enter second word: ")

if len(word1) != len(word2):
    print("Not Anagram")
else:
    for letter in word1:
        if word1.count(letter) != word2.count(letter):
            print("Not Anagram")
            break
    else:
        print("Anagram")