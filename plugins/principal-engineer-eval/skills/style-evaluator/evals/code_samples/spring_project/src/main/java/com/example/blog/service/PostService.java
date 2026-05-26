package com.example.blog.service;

import com.example.blog.model.Post;
import com.example.blog.repository.PostRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Service
public class PostService {

    private final PostRepository postRepository;

    @Autowired
    public PostService(PostRepository postRepository) {
        this.postRepository = postRepository;
    }

    @Transactional(readOnly = true)
    public List<Post> listPosts(int page, int size) {
        return postRepository.findAll(
                PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"))
        ).getContent();
    }

    @Transactional(readOnly = true)
    public Optional<Post> findPost(long id) {
        return postRepository.findById(id);
    }

    @Transactional
    public Post createPost(Post post) {
        post.setCreatedAt(Instant.now());
        post.setUpdatedAt(Instant.now());
        return postRepository.save(post);
    }

    @Transactional
    public Optional<Post> updatePost(long id, Post update) {
        return postRepository.findById(id).map(existing -> {
            existing.setTitle(update.getTitle());
            existing.setBody(update.getBody());
            existing.setUpdatedAt(Instant.now());
            return postRepository.save(existing);
        });
    }

    @Transactional
    public boolean deletePost(long id) {
        if (!postRepository.existsById(id)) {
            return false;
        }
        postRepository.deleteById(id);
        return true;
    }
}
